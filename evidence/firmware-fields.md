# Saved firmware-field interpretation

Source: SocketSetup IFR extraction for Dell BIOS 2.50.2, archived October 28, 2026.

The saved extraction declares SocketCommonRcConfig (GUID 4402ca38-808f-4279-bcec-5baf8d59092f), size 0x73 and attributes 0x7. Form locations 0x97BF and 0x9817 identify the base and granularity fields.

| Data offset | Width | Field | Enum meanings |
|---|---|---|---|
| 0x00 | 32 bits | MMIO High Base | 0=56T, 1=40T, 2=24T, 3=16T, 4=4T, 5=1T |
| 0x04 | 16 bits | MMIO High Granularity Size | 0=1G, 1=4G, 2=16G, 3=64G, 4=256G, 5=1024G |

These are enum indices, not literal addresses or byte sizes. The granularity help describes allocation in multiples of a unit and up to 32 units. The interpretation is specific to the extracted firmware; length and fingerprint matches alone cannot prove a different BIOS has identical semantics.

The full vendor firmware image/extraction is not redistributed.

Archived extraction SHA256: `bd5d22f3066a7ff3b8f477d0e535c335e3b6e3f573722e57818d84ee27fe1dd4`.
