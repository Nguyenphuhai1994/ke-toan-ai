# Kế toán AI

Dự án đang xây dựng, chưa phải ứng dụng hoàn chỉnh. Không triển khai production hoặc sử dụng dữ liệu thật.

Hiện có bộ khung Django thử nghiệm và mô hình thu chi, công nợ, thanh toán từng phần. Chưa có giao diện, phân quyền, chứng từ, AI hoặc bot. Logic đồng thời chưa được xác minh; SQLite không đảm bảo khóa hàng như PostgreSQL.

## Chạy kiểm thử bằng Docker

```sh
docker build -t ke-toan-ai-test .
docker run --rm ke-toan-ai-test
```

Dockerfile mặc định chạy `python manage.py test core`, không khởi chạy ứng dụng web. Chưa có cấu hình triển khai VPS, sao lưu, 2FA, quét tệp hoặc hệ thống bảo vệ dữ liệu hoàn chỉnh. Chỉ dùng môi trường cô lập và dữ liệu giả.
