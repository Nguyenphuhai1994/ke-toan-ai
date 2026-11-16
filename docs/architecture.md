# Kiến trúc và kế hoạch MVP

## Trạng thái và phạm vi

Đây là thiết kế đề xuất, không phải mô tả chức năng đã hoàn thành. README xác định dự án chưa hoàn chỉnh, chỉ dùng dữ liệu giả và không triển khai production. Hiện có bộ khung Django và các model Company, Transaction, Obligation, Payment cùng test model; chưa có giao diện, phân quyền, chứng từ, AI hoặc bot hoàn chỉnh. Logic đồng thời chưa được xác minh trên PostgreSQL; SQLite không đảm bảo khóa hàng tương đương. MVP phục vụ một công ty trong một cài đặt; không cam kết đa công ty hay tuân thủ kế toán/pháp lý nếu chưa được chuyên gia thẩm định.

## Kiến trúc đề xuất

- Django phục vụ giao diện web và nghiệp vụ; PostgreSQL là nguồn dữ liệu giao dịch. Docker đóng gói dịch vụ web và cơ sở dữ liệu, lưu dữ liệu trên volume riêng; HTTPS qua reverse proxy khi triển khai được chấp thuận.
- Mỗi bản ghi nghiệp vụ, chứng từ và audit gắn company; mọi truy vấn, thao tác và tải file đều kiểm tra membership và giới hạn theo company phía máy chủ, kể cả khi MVP chỉ có một công ty. Ràng buộc liên kết cùng công ty; không tin company ID do client cung cấp. Đây là nền tảng mở rộng, không tự coi là cách ly tenant hoàn chỉnh.
- Vai trò đề xuất: quản trị viên quản lý thành viên và cấu hình; kế toán lập và xử lý thu chi, công nợ, chứng từ; người xem chỉ đọc. Mặc định từ chối, kiểm tra quyền ở từng endpoint và đối tượng; ghi audit người thực hiện, thời gian và thay đổi quan trọng, không ghi secret hoặc nội dung nhạy cảm không cần thiết.
- Model hiện tại gồm công ty, giao dịch thu/chi, khoản phải thu/phải trả và liên kết thanh toán. Bổ sung membership, chứng từ, audit và quy trình điều chỉnh theo nhu cầu; dùng Decimal, quy tắc làm tròn rõ ràng, ràng buộc số tiền dương và lưu lịch sử thay vì âm thầm sửa số liệu đã chốt.

## Thanh toán và đồng thời

Một công nợ có thể được thanh toán nhiều lần; số dư bằng số tiền công nợ trừ tổng các khoản thanh toán hợp lệ. Mỗi giao dịch thanh toán hiện liên kết tối đa một công nợ; chia một giao dịch cho nhiều công nợ cần thiết kế phân bổ riêng. Chỉ cho phép cùng công ty, đúng chiều thu/chi và tổng không vượt công nợ. Các thao tác tạo, sửa, hủy thanh toán và sửa công nợ/giao dịch liên quan phải đi qua service thống nhất, trong `transaction.atomic`, khóa các hàng liên quan bằng `select_for_update` theo thứ tự cố định, đọc lại số dư sau khi khóa rồi kiểm tra và ghi. Dùng khóa idempotency cho yêu cầu lặp; ngăn đường ghi bỏ qua service và kiểm tra các ràng buộc ở database khi khả thi. Định nghĩa rõ hủy/đảo và lưu audit; không xóa âm thầm lịch sử. Kiểm thử race với kết nối PostgreSQL độc lập, bao gồm sửa giao dịch đồng thời với thanh toán và yêu cầu trùng; không coi test SQLite là bằng chứng an toàn đồng thời.

## Chứng từ riêng tư và tích hợp

- File tải lên vào vùng cách ly riêng, ngoài web root, không có URL công khai; giới hạn dung lượng, loại thực tế, tên an toàn và quyền truy cập. Quét malware bất đồng bộ; chỉ chuyển sang vùng riêng tư sau kết quả sạch. Lỗi hoặc thiếu máy quét giữ cách ly và từ chối tải xuống; file nghi nhiễm bị cách ly để xử lý theo chính sách. Tải xuống qua endpoint đã xác thực, phân quyền theo công ty và đối tượng; không ghi file hay dữ liệu thật vào Git.
- AI và Zalo mặc định tắt; không gửi dữ liệu hoặc gọi API cho đến khi cấu hình, kiểm tra bảo mật, quyền sử dụng, đồng ý phù hợp và yêu cầu pháp lý được đáp ứng. Chưa giả định tích hợp đã hoạt động. Trước khi bật cần giới hạn dữ liệu, quản lý secret, kiểm soát truy cập, thời hạn lưu và cơ chế tắt; kết quả AI chỉ là gợi ý có người duyệt, không tự hạch toán.

## Bảo mật và vận hành

Bắt buộc 2FA cho tài khoản đặc quyền, thiết kế khôi phục an toàn và mở rộng cho người dùng khác; bảo vệ phiên, CSRF, mật khẩu, giới hạn đăng nhập và quản lý secret ngoài repository. Sao lưu mã hóa PostgreSQL và kho file riêng tư theo lịch, lưu bản sao ngoài máy chủ, giới hạn quyền và thời hạn lưu; giám sát kết quả, định kỳ diễn tập khôi phục đồng bộ database/file trên môi trường cô lập. Xác định RPO/RTO với chủ sở hữu trước production; không xóa volume hoặc backup trong quy trình thông thường.

## Thứ tự thực hiện và kiểm thử

1. Chốt nghiệp vụ, quyền, phạm vi pháp lý và tiêu chí nghiệm thu; cấu hình PostgreSQL, migration và môi trường phát triển dùng dữ liệu giả.
2. Xây membership, phân quyền theo công ty, audit và 2FA; kiểm thử truy cập chéo công ty, đối tượng và vai trò, kể cả URL file.
3. Hoàn thiện service thu chi, công nợ, thanh toán từng phần và điều chỉnh; test số dư, vượt thanh toán, hướng giao dịch, retry, rollback và cạnh tranh trên PostgreSQL.
4. Xây quy trình upload/cách ly/quét/tải riêng tư; test file độc hại, sai định dạng, quét lỗi và truy cập trái phép.
5. Cấu hình Docker, sao lưu và diễn tập khôi phục; chạy unit, integration, migration, kiểm thử bảo mật và build trong CI. Chỉ xem xét AI/Zalo sau khi đáp ứng các điều kiện ở trên.

Tài liệu này không xác nhận các bước trên đã được triển khai, kiểm thử hoặc đưa lên production.
