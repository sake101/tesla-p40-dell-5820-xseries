"""Offline verifier for this case's saved dmpstore records. Never writes firmware or files."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import uuid
import zlib

NAME = 'SocketCommonRcConfig'
GUID = uuid.UUID('4402ca38-808f-4279-bcec-5baf8d59092f').bytes_le

def parse_save(blob):
    if len(blob) < 8:
        raise ValueError('Truncated record header')
    name_size, data_size = struct.unpack_from('<II', blob)
    expected_name = (NAME + '\0').encode('utf-16-le')
    if name_size != len(expected_name) or data_size != 115:
        raise ValueError('Unexpected name/data length; this verifier is case-specific')
    expected_size = 8 + name_size + 16 + 4 + data_size + 4
    if len(blob) != expected_size:
        raise ValueError('Truncated record or trailing data')
    offset = 8
    if blob[offset:offset + name_size] != expected_name:
        raise ValueError('Unexpected variable name')
    offset += name_size
    if blob[offset:offset + 16] != GUID:
        raise ValueError('Unexpected variable GUID')
    offset += 16
    if struct.unpack_from('<I', blob, offset)[0] != 7:
        raise ValueError('Unexpected variable attributes')
    offset += 4
    if zlib.crc32(blob[:-4]) & 0xffffffff != struct.unpack_from('<I', blob, len(blob) - 4)[0]:
        raise ValueError('CRC mismatch')
    data = blob[offset:offset + data_size]
    if data[2:4] != b'\0\0' or data[7] != 2 or data[9] != 1:
        raise ValueError('Unknown case-layout fingerprint')
    return data

def compare(before_blob, after_blob, verify_blob=None):
    before, after = parse_save(before_blob), parse_save(after_blob)
    if struct.unpack_from('<I', before)[0] != 0 or struct.unpack_from('<H', before, 4)[0] != 0:
        raise ValueError('Before fields differ from this documented case')
    changed = [i for i, pair in enumerate(zip(before, after)) if pair[0] != pair[1]]
    if changed != [4] or after[4] != 3:
        raise ValueError('Expected only offset 4 to change from 0 to 3')
    if verify_blob is not None and parse_save(verify_blob) != after:
        raise ValueError('Post-reboot data differs from the immediate readback')
    return {'data_bytes': len(before), 'changed_offsets': changed,
            'base_enum_before_and_after': 0, 'granularity_enum_before': 0,
            'granularity_enum_after': 3, 'post_reboot_matches': verify_blob is not None,
            'sha256_before_record': hashlib.sha256(before_blob).hexdigest(),
            'sha256_after_record': hashlib.sha256(after_blob).hexdigest(),
            **({'sha256_verify_record': hashlib.sha256(verify_blob).hexdigest()} if verify_blob is not None else {})}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    try:
        result = compare(args.before.read_bytes(), args.after.read_bytes(), args.verify.read_bytes() if args.verify else None)
    except (OSError, ValueError) as error:
        parser.exit(1, f'REFUSED: {error}\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
