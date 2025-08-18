from PIL import Image
import os

# 스크립트 파일의 디렉토리 경로를 가져옵니다.
script_dir = os.path.dirname(os.path.abspath(__file__))

# 이미지 파일 경로 설정
source_folder = os.path.join(script_dir, 'images')
source_file = 'tbcicon.png'
target_file = 'tbcicon.ico'

# 전체 경로 생성
source_path = os.path.join(source_folder, source_file)
target_path = os.path.join(source_folder, target_file)

# 이미지 열기
try:
    img = Image.open(source_path)
    
    # ICO 형식으로 저장 (다양한 해상도 포함 가능)
#    icon_sizes = [(16,16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon_sizes = [(32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(target_path, format='ICO', sizes=icon_sizes)
    
    print(f"'{source_path}'를 '{target_path}'로 성공적으로 변환했습니다.")

except FileNotFoundError:
    print(f"오류: '{source_path}' 파일을 찾을 수 없습니다.")
except Exception as e:
    print(f"이미지 변환 중 오류가 발생했습니다: {e}")
