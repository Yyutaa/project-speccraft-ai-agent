# ExportFlow Sample Repository Guide

- Frontend uses React and consumes an explicit API contract.
- Backend uses a layered controller/application/domain/infrastructure structure.
- Large files must be streamed; request threads must not wait for row processing.
- Import jobs and reliable messages are committed transactionally; consumers are idempotent.
- This repository is an anonymous course fixture and contains no enterprise business data.
