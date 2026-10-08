# DriverManagementPlatform

Monorepo khởi tạo cho nền tảng quản lý tài xế. Cấu trúc hiện tại là bộ khung thư mục; frontend, backend và hạ tầng sẽ được bổ sung theo từng giai đoạn.

Xem [AGENTS.md](AGENTS.md) để biết cấu trúc, ranh giới module và quy ước đóng góp.

## Thành phần dự kiến

- `apps/web`: React web app
- `apps/mobile`: React Native mobile app
- `services/api`: FastAPI backend, chia theo domain
- `services/agent-orchestrator`: điều phối agent và workflow
- `services/event-consumer`: xử lý Kafka events
- `services/data-processing`: xử lý dữ liệu
- `infra/`: Docker, Kafka, database và monitoring

Chưa có lệnh build/test cho đến khi các ứng dụng và cấu hình tương ứng được khởi tạo.
