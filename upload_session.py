from src.repositories.supabase_repository import SupabaseRepository

def upload():
    repo = SupabaseRepository()
    success = repo.upload_file("sessions", "auth_state.json", "auth_state.json")
    if success:
        print("✅ Đã upload file auth_state.json lên Supabase thành công!")
        print("Bây giờ bạn có thể bật USE_PERSISTENT_SESSION=true trong file .env và chạy lại main.py.")
    else:
        print("❌ Lỗi: Upload thất bại. Vui lòng kiểm tra lại cấu hình Supabase trong .env hoặc chắc chắn file auth_state.json đã tồn tại ở máy của bạn.")

if __name__ == "__main__":
    upload()
