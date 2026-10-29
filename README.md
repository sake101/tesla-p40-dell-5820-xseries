# Tesla P40 on Dell Precision 5820 X-Series: i9-10900X, BIOS 2.50.2

A documented one-machine result, October 28–29, 2026: a Tesla P40 that previously prevented POST now boots beside a Radeon Pro W5500 and executes CUDA inference after a change to the firmware's high-MMIO allocation setting.

The useful addition to earlier reports is the **Core X / X299 configuration and BIOS-specific field interpretation**, plus actual compute results. This is not a claim to have discovered the general high-MMIO workaround or a universal firmware patch.

## Credit and prior work

- [kaykavous-ai's P40 / Xeon 5820 guide](https://github.com/kaykavous-ai/tesla-p40-dell-precision-5820) documents BIOS 2.41.0 and the original diagnostic approach and dump format.
- [ReBarUEFI discussion #331](https://github.com/xCuri0/ReBarUEFI/discussions/331) contains the earlier workstation research. In particular, **enomam's October 26, 2026 report** describes a Xeon W-2155 / 5820 / BIOS 2.48.0 with two V100 32 GB cards, changing granularity to 64G while retaining the 56T base.
- The workstation owner performed physical changes and UEFI operations. Claude and OpenAI Codex assisted with research, firmware interpretation, scripts, and evidence review. This report was edited with Codex.

## Tested configuration

| Component | Configuration in this case |
|---|---|
| Workstation | Dell Precision 5820 Tower **X-Series**, board 0XNJ2Y |
| CPU / RAM | Intel Core i9-10900X; 96 GB installed |
| BIOS | **2.50.2**; this is the tested version, not a recommendation to update |
| Operating system | Windows 11 Pro |
| Display card | AMD Radeon Pro W5500, slot 1 |
| Compute card | NVIDIA Tesla P40 24 GB, slot 2 |
| NVIDIA driver | 582.78, TCC in the recorded working setup |
| Power / cooling | 950 W Dell PSU; adapter to the P40's EPS-style input; external blower |

Before the change, the owner observed repeated power cycles, a steady white power LED, no Dell logo, and no NVIDIA device in Windows; removing the P40 allowed boot. Above-4G mapping was already enabled. That visible switch alone was insufficient in this case.

Do not copy a cable recommendation from connector shape alone. The P40 power input and ordinary PCIe 8-pin power have different pinouts. The exact harness, PSU connections and airflow must be checked for each build.

## What changed

The extracted **BIOS 2.50.2 SocketSetup IFR** defines this EFI variable:

| Property | Value |
|---|---|
| Name | `SocketCommonRcConfig` |
| GUID | `4402ca38-808f-4279-bcec-5baf8d59092f` |
| Data length | `0x73` = 115 bytes |
| Attributes in the saved records | `0x7` |
| Offset `0x00` | 32-bit **MMIO High Base** enum; 0 means **56T** |
| Offset `0x04` | 16-bit **MMIO High Granularity Size** enum |

Granularity options in that extraction: 0=1G, 1=4G, 2=16G, **3=64G**, 4=256G, 5=1024G. Both fields have enum range 0–5.

The saved before/after records show **only byte offset `0x04` changed, `00` → `03`**. The full 16-bit field changed from `00 00` to `03 00`; the base field stayed zero, meaning **56T**, not address zero.

This distinction matters: zero enum values in this firmware do not mean a zero-sized or zero-based window. The IFR description explains that high-MMIO resources are allocated in granularity units. Increasing the recorded setting from 1G to 64G is consistent with accommodating the P40's large BAR. Successful boot and compute after the change support this explanation; no firmware-internal resource-allocation trace was captured.

The earlier Xeon guide uses different base/granularity values. Its base bytes must not be transferred to this BIOS: interpreted as this firmware's 32-bit enum, they would be outside the documented range.

See [sanitized evidence](evidence/verification.json) for dump hashes and the independently checked change, and [the field summary](evidence/firmware-fields.md) for extraction provenance.

## Procedure used in this case

Hidden firmware-variable writes can prevent boot. Establish a recovery method and preserve disk-encryption recovery information off the machine before attempting firmware work. This record applies to one configuration; verify the matching BIOS's IFR and your own saved variable before considering a write.

1. With the P40 removed, prepare an EDK2 x64 UEFI shell on FAT32 media. The owner temporarily disabled Secure Boot for the unsigned shell and prepared BitLocker recovery/protection handling. Do not leave those protections suspended after the work.
2. In the shell, read and save the existing variable. These two commands **read NVRAM**; the second writes a backup file to your chosen USB filesystem. Substitute the filesystem actually containing your USB, rather than assuming `fs0:`.

   ```text
   dmpstore -guid 4402ca38-808f-4279-bcec-5baf8d59092f SocketCommonRcConfig
   dmpstore -guid 4402ca38-808f-4279-bcec-5baf8d59092f -s fs0:\rc-before.bin SocketCommonRcConfig
   ```

3. Back in the OS, inspect that saved record against the exact BIOS field mapping. In this case the variable was 115 bytes, base enum 0, granularity enum 0. A payload was built from **that machine's own freshly saved data**, preserving every byte except offset 4. No other machine's full payload was used.
4. The owner used the UEFI shell's `setvar` command with the existing GUID/attributes and the complete inspected value, changing granularity to enum 3. **This repository intentionally contains no ready-to-run write script or universal hex payload.** The existing upstream references document the command form; their field values must be interpreted against the matching firmware.
5. Immediately save `rc-after.bin`, reboot through the one-time boot menu, and save a new readback such as `rc-verify.bin`. Check that the exact intended change persisted and every other byte was preserved. The read-only verifier below performs that comparison offline.
6. Power off, disconnect AC, install and power the P40 with verified wiring and active cooling, then boot. The owner and earlier reports describe multiple boot cycles/delays; they are an observation, not a universal normal count or a reason to ignore diagnostic LED codes.
7. Install the appropriate driver and verify enumeration, BAR1 allocation, and then an actual compute workload. Recorded BAR1 was **32768 MiB**. BAR1 aperture size is distinct from the P40's 24 GB VRAM capacity. TCC devices need not appear in Task Manager's GPU charts.
8. Restore the intended Secure Boot and disk-encryption protections and check operation again. Any firmware/security setting change requires fresh verification; do not assume a saved workaround survives it.

**Persistence caveats:** earlier reports warn that Save/Apply in F2 Setup can restore the setup copy of this variable. Avoid unnecessary setup saves after the change. CMOS reset and BIOS updates can reset firmware state, but this report does not establish that every update always erases the setting; some upstream owners report persistence. Re-read and re-evaluate before any further write. Do not blindly repeat this change on a working machine.

If the card prevents POST, removing it may restore the earlier boot configuration; that does not undo the variable change. Recovering altered NVRAM may require the correct Dell service procedure. Never bulk-restore another machine's firmware settings.

## Read-only evidence checker

Python 3, standard library only. It reads saved files; it neither accesses firmware/GPU devices nor creates a payload:

```text
python scripts/verify_dumps.py rc-before.bin rc-after.bin --verify rc-verify.bin
python -m unittest discover -s tests -v
```

It validates record structure, CRC, variable identity, attributes and the known case layout; then requires base enum 0, granularity 0→3, and **exactly one changed byte at offset 4**. A successful comparison is not approval to write firmware, nor proof of general hardware compatibility.

## Compute and thermal results

Selected existing benchmark records, not new measurements run for publication:

| Workload | Recorded result | Scope |
|---|---|---|
| Gemma 4 12B QAT, UD-Q4_K_XL | **26.49–26.86 tokens/s** | llama.cpp b10622, 150 W, 128 generated tokens, three repetitions, separate flash-attention settings |
| Gemma 4 26B-A4B QAT, UD-Q4_K_XL | **57.73–58.92 tokens/s** | Same short single-sequence test; MoE architecture, not a claim that a dense 26B runs this fast |
| Gemma 4 26B-A4B at 16,384-token depth | **50.57 tokens/s** | 128 generated tokens; different prompt/context workload |
| SDXL base 1024×1024, 20 steps, two images, sd.cpp | **149.4 s FP16 / 264.5 s FP32** | Wrapper wall times including startup; peak VRAM 14,604 / 20,170 MiB; both logs confirm two saved images |
| E4B decode load, 150 W | **30.1 minutes, maximum 76°C** | Last ten minutes averaged 75.8°C and 147.5 W; not a weekend or continuous-duty qualification |

[Selected benchmark rows](evidence/text-speed.csv), [thermal matrix](evidence/thermal-matrix.csv), and [sanitized log excerpts](evidence/compute-excerpts.txt) preserve the scope of these numbers. GPU compute is demonstrated; this does not qualify production model accuracy, unrestricted concurrency, or long-term hardware reliability.

The short thermal sweep reached 83°C and aborted at 175–250 W with this cooling setup. Changing the tested NZXT fan-control percentages did not demonstrate better cooling. At 125 W the short test peaked at 64°C; at 150 W, 73–74°C. These measurements belong to this particular installation. The later 30-minute run is stronger evidence than the short cells but still insufficient to claim unattended long-weekend stability. Power-limit throttling is distinct from thermal throttling; no universal efficiency claim is made here.

Some original benchmark harnesses recorded `ok` for failed or empty jobs. This report uses only selected rows with supporting output, not the queue's status label. It does not publish the private email, accounting, or media evaluation datasets.

## Scope, privacy and license

The evidence packet contains hashes, field/diff metadata, selected performance rows and sanitized excerpts. It omits raw firmware images/payloads, serial numbers, UUIDs, recovery material, local account paths and business content. A full private dump is not required to understand the recorded change.

Documentation and the new read-only verifier are MIT licensed; attribution is in [LICENSE](LICENSE). Dell/NVIDIA/Intel names remain their respective owners' marks. No vendor endorsement or support is implied.
