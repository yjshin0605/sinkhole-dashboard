import streamlit as st
import pandas as pd
import random
import io

# ---------------------------------------------------------
# 1. 데이터 생성 함수 (사용자 정의 로직 유지)
# ---------------------------------------------------------
def generate_mock_data(count=20):
    """
    [인덱스, 3차원 좌표, 공극 크기] 구조를 가진 가상 데이터를 생성합니다.
    """
    data = []
    for i in range(1, count + 1):
        # 가상의 크기 데이터 (지름)
        width = round(random.uniform(0.3, 8.0), 2)
        
        # 위험도 등급 판단 로직 (사용자 정의)
        if width > 4.0:
            risk = "긴급"
        elif width > 1.0:
            risk = "우선"
        else:
            risk = "일반"

        # 요청하신 데이터 구조
        entry = {
            "index": i,
            "coordinates_3d": {
                "latitude": 37.5 + random.uniform(0.01, 0.1),
                "longitude": 126.9 + random.uniform(0.01, 0.1),
                "depth_z": round(random.uniform(2.0, 15.0), 2)
            },
            "void_size": {
                "width": width,
            },
            "risk_level": risk
        }
        data.append(entry)
    return data

# ---------------------------------------------------------
# 2. 화면 구성 (Streamlit 라이브러리 사용)
# ---------------------------------------------------------
# 페이지 제목과 아이콘 설정
st.set_page_config(page_title="지하 공극 리포트", page_icon="🕳️", layout="wide")

st.title("🕳️ 지하 공극(Sinkhole) 리포트")

# 데이터 상태 관리 (새로고침해도 데이터 유지)
if 'void_data' not in st.session_state:
    st.session_state['void_data'] = generate_mock_data()

# 사이드바: 데이터 새로 만들기 버튼
with st.sidebar:
    st.header("⚙️ 설정")
    if st.button("🔄 새로운 데이터 생성", use_container_width=True):
        st.session_state['void_data'] = generate_mock_data()
        st.success("데이터가 갱신되었습니다!")

data = st.session_state['void_data']

# ---------------------------------------------------------
# 3. 데이터 가공 (CSV 변환 준비)
# ---------------------------------------------------------
# 중첩된 JSON 데이터를 엑셀처럼 보기 좋게 펴줍니다 (Flatten)
flattened_data = []
for item in data:
    flattened_data.append({
        "Index": item['index'],
        "위험도": item['risk_level'],
        "위도": item['coordinates_3d']['latitude'],
        "경도": item['coordinates_3d']['longitude'],
        "심도(m)": item['coordinates_3d']['depth_z'],
        "너비(m)": item['void_size']['width'],
    })

# 판다스 데이터프레임으로 변환
df = pd.DataFrame(flattened_data)

# ---------------------------------------------------------
# 4. 화면 표시 및 다운로드 버튼
# ---------------------------------------------------------
col_left, col_right = st.columns([3, 1])

with col_left:
    st.subheader("📋 탐지 데이터 목록")
    # 화면에 표 그리기
    st.dataframe(df, use_container_width=True, height=500)

with col_right:
    st.subheader("💾 리포트 다운로드")
    st.info("CSV 파일로 다운로드합니다.")
    
    # [수정됨] CSV 한글 깨짐 해결 (BOM 추가)
    # 기존 io.StringIO 방식 대신 바이트 인코딩을 직접 수행합니다.
    csv_data = df.to_csv(index=False).encode('utf-8-sig')
    
    # 다운로드 버튼 생성
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv_data,
        file_name="report.csv",
        mime="text/csv",
        use_container_width=True,
        type="primary"
    )
    
    st.divider()
    with st.expander("JSON 원본 보기"):
        st.json(data[0])