#!/usr/bin/env python3
"""Test ARM64 Android ksud against temporary image files, never partitions."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile


def cpio_entry(name, data, mode=0o100755):
    encoded = name.encode() + b'\0'
    fields = [1, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(encoded), 0]
    entry = b'070701' + b''.join(f'{value:08x}'.encode() for value in fields) + encoded
    entry += b'\0' * (-len(entry) % 4)
    return entry + data + b'\0' * (-len(data) % 4)


def ramdisk_entries(image):
    data = image.read_bytes()
    assert data[:8] == b'ANDROID!'
    kernel_size, ramdisk_size = struct.unpack_from('<II', data, 8)
    assert struct.unpack_from('<I', data, 40)[0] == 4
    offset = 4096 + ((kernel_size + 4095) // 4096) * 4096
    ramdisk = data[offset:offset + ramdisk_size]
    if ramdisk.startswith(b'\x1f\x8b'):
        ramdisk = gzip.decompress(ramdisk)
    assert ramdisk.startswith(b'070701')
    entries = {}
    position = 0
    while True:
        assert ramdisk[position:position + 6] == b'070701'
        fields = [int(ramdisk[position + 6 + n * 8:position + 14 + n * 8], 16)
                  for n in range(13)]
        size, namesize = fields[6], fields[11]
        position += 110
        name = ramdisk[position:position + namesize - 1].decode()
        position += namesize
        position = (position + 3) & ~3
        contents = ramdisk[position:position + size]
        assert len(contents) == size
        position = (position + size + 3) & ~3
        if name == 'TRAILER!!!':
            return entries
        assert name not in entries
        entries[name] = contents


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True, type=Path)
    parser.add_argument('--official', required=True, type=Path)
    parser.add_argument('--qemu', required=True, type=Path)
    parser.add_argument('--android-root', required=True, type=Path)
    parser.add_argument('--providers', required=True, type=Path)
    parser.add_argument('--ksuinit', required=True, type=Path)
    args = parser.parse_args()
    prefix = [str(args.qemu.resolve()), '-L', str(args.android_root.resolve()),
              '-E', f'LD_LIBRARY_PATH={args.android_root.resolve()}/system/lib64']

    def run(binary, *arguments, success=True):
        result = subprocess.run(prefix + [str(binary.resolve()), *map(str, arguments)],
                                capture_output=True, text=True, timeout=90)
        if success:
            assert result.returncode == 0, result.stdout + result.stderr
        return result

    assert run(args.binary, '--version').stdout == run(args.official, '--version').stdout
    for command in [(), ('module',), ('boot-patch',), ('boot-info',), ('debug',)]:
        assert run(args.binary, *command, '--help').stdout == \
            run(args.official, *command, '--help').stdout.replace(
                'Usage: ' + args.official.name, 'Usage: ' + args.binary.name)
    kmis = run(args.binary, 'boot-info', 'supported-kmis').stdout.splitlines()
    assert kmis == run(args.official, 'boot-info', 'supported-kmis').stdout.splitlines()
    assert len(kmis) == 8
    print('PASS: version, command interfaces and eight supported KMIs preserved')

    catalog = json.loads((args.providers / 'providers.json').read_text())
    with tempfile.TemporaryDirectory(prefix='aera-ksud-images-') as directory:
        root = Path(directory)
        for helper in ['ksuinit', 'busybox', 'bootctl', 'waitsys']:
            new, old = root / (helper + '.new'), root / (helper + '.official')
            run(args.binary, 'debug', 'extract-binary', helper, new)
            run(args.official, 'debug', 'extract-binary', helper, old)
            assert new.read_bytes() == old.read_bytes(), helper
        print('PASS: all four embedded helper binaries match the official release')

        original_init = b'AERA synthetic init; never boot this test image\n'
        cpio = cpio_entry('init', original_init) + cpio_entry('TRAILER!!!', b'', mode=0)
        compressed = gzip.compress(cpio, mtime=0)
        header = struct.pack('<8sIIII4II1536sI', b'ANDROID!', 0, len(compressed),
                             0, 1584, 0, 0, 0, 0, 4, b'', 0)
        image = root / 'stock-init_boot.img'
        image.write_bytes(header.ljust(4096, b'\0') + compressed +
                          b'\0' * (-len(compressed) % 4096))
        original_hash = hashlib.sha256(image.read_bytes()).digest()
        count = 0
        for provider in catalog['providers']:
            for asset in provider['assets']:
                module = args.providers / provider['id'] / asset['name']
                assert hashlib.sha256(module.read_bytes()).hexdigest() == asset['sha256']
                filename = f"{provider['id']}-{asset['kmi']}.img"
                result = run(args.binary, 'boot-patch', '-b', image, '-m', module,
                             '--partition', 'init_boot', '--kmi', asset['kmi'],
                             '-o', root, '--out-name', filename)
                entries = ramdisk_entries(root / filename)
                assert entries['kernelsu.ko'] == module.read_bytes()
                assert entries['init'] == args.ksuinit.read_bytes()
                assert entries['init.real'] == original_init
                assert 'Done!' in result.stdout
                count += 1
        assert count == 12
        assert hashlib.sha256(image.read_bytes()).digest() == original_hash
        failure = run(args.binary, 'boot-patch', '-b', image, '-m', root / 'missing.ko',
                      '--partition', 'init_boot', '--kmi', 'android14-6.1',
                      '-o', root, '--out-name', 'must-not-exist.img', success=False)
        assert failure.returncode != 0
        assert not (root / 'must-not-exist.img').exists()
        print('PASS: all 12 provider/KMI combinations patch correctly; missing module fails safely')

        # QEMU -L maps this known ramdisk path into the test Android root.
        provider = next(item for item in catalog['providers'] if item['id'] == 'kernelsu')
        for asset in provider['assets']:
            name = asset['kmi'] + '_kernelsu.ko'
            extracted = root / name
            run(args.binary, 'debug', 'extract-binary', name, extracted)
            module = args.providers / provider['id'] / asset['name']
            assert extracted.read_bytes() == module.read_bytes()
        run(args.binary, 'boot-patch', '-b', image, '--partition', 'init_boot',
            '--kmi', 'android14-6.1', '-o', root, '--out-name', 'auto.img')
        assert ramdisk_entries(root / 'auto.img')['kernelsu.ko'] == \
            (args.providers / 'kernelsu/lkm-aarch64-android14-6.1_kernelsu.ko').read_bytes()
        print('PASS: default KernelSU lookup loads AERA external modules')
    print('PASS: all validation used temporary files; no partition writes')


if __name__ == '__main__':
    main()
