# Known limitations

- CSV inference can change types; use Parquet or validate schemas for financial work.
- The local executor returns exactly one non-null scalar per metric cell.
- Schema rename detection is deliberately disabled without an explicit mapping.
- DuckDB memory configuration and process termination are best-effort resource controls, not an OS-level sandbox.
- Local execution is tested on Windows in this release workspace. Linux packaging is designed and documented but pending separate validation; macOS is unverified.
- The report digest detects report modifications but does not sign or authenticate it.
- No marketplace approval, package-name availability, or license grant has been obtained.
