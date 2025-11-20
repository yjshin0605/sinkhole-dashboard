import streamlit as st
import pandas as pd
import random
import io
import os
import urllib.request
from datetime import datetime, timedelta
from fpdf import FPDF
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# ---------------------------------------------------------
# 0. 초기 설정 (폰트 및 주소 변환기)
# ---------------------------------------------------------
@st.cache_resource
def get_korean_font():
    font_path = "NanumGothic.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        try:
            urllib.request.urlretrieve(url, font_path)
        except:
            st.error("폰트 다운로드 실패. PDF에서 한글이 깨질 수 있습니다.")
    return font_path

# 주소 변환 함수 (캐싱하여 속도 향상)
@st.cache_data(show_spinner=False)
def get_address_batch(coords_list):
    """
    좌표 리스트를 받아 주소 리스트로 변환합니다.
    """
    geolocator = Nominatim(user_agent="void_detection_demo_v2")
    geocode = RateLimiter(geolocator.reverse, min_delay_seconds=0.1)
    
    addresses = []
    progress_bar = st.progress(0, text="좌표를 주소로 변환 중입니다...")
    
    for i, (lat, lon) in enumerate(coords_list):
        try:
            location = geocode((lat, lon), language='ko', timeout=5)
            if location:
                addr = location.address.replace("대한민국", "").strip()
                if str(location.raw.get('address', {}).get('postcode')) in addr:
                    addr = addr.replace(location.raw.get('address', {}).get('postcode'), "")
                addresses.append(addr.strip(', '))
            else:
                addresses.append("주소 미확인")
        except:
            addresses.append("통신 오류")
        
        progress_bar.progress((i + 1) / len(coords_list))
    
    progress_bar.empty()
    return addresses

# ---------------------------------------------------------
# 1. PDF 생성 클래스
# ---------------------------------------------------------
class PDFReport(FPDF):
    def header(self):
        self.add_font('NanumGothic', '', 'NanumGothic.ttf')
        self.set_font('NanumGothic', '', 10)
        self.set_font('NanumGothic', '', 20)
        self.cell(0, 15, '지하 공극(Sinkhole) 탐지 리포트', align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('NanumGothic', '', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

@st.cache_data
def generate_pdf_report(df, summary_stats):
    get_korean_font()
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # 요약 섹션
    pdf.set_font('NanumGothic', '', 14)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, "  1. 탐지 요약", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(5)
    pdf.set_font('NanumGothic', '', 11)
    pdf.cell(0, 8, f"- 총 탐지 건수: {summary_stats['total']} 건", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"- 긴급 조치 필요: {summary_stats['critical']} 건", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"- 평균 공극 너비: {summary_stats['avg_width']} m", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # 테이블 섹션
    pdf.set_font('NanumGothic', '', 14)
    pdf.cell(0, 10, "  2. 상세 데이터 목록", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(5)

    pdf.set_font('NanumGothic', '', 10)
    pdf.set_fill_color(52, 152, 219)
    pdf.set_text_color(255, 255, 255)
    
    # [PDF는 여전히 주소를 유지하여 가독성 확보]
    col_widths = [15, 20, 85, 25, 25] 
    headers = ['Index', '위험도', '위치 (주소)', '심도(m)', '너비(m)']
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 10, h, align='C', fill=True)
    pdf.ln()

    pdf.set_text_color(0, 0, 0)
    fill = False 
    
    for index, row in df.iterrows():
        pdf.set_font('NanumGothic', '', 9)
        
        if row['위험도'] == '긴급':
            pdf.set_text_color(192, 57, 43)
        else:
            pdf.set_text_color(0, 0, 0)
        pdf.set_fill_color(245, 245, 245)
        
        pdf.cell(col_widths[0], 8, str(row['Index']), align='C', fill=fill)
        pdf.cell(col_widths[1], 8, str(row['위험도']), align='C', fill=fill)
        
        # 주소 출력
        pdf.set_font('NanumGothic', '', 7)
        pdf.cell(col_widths[2], 8, str(row['주소']), align='L', fill=fill)
        pdf.set_font('NanumGothic', '', 9)

        pdf.cell(col_widths[3], 8, str(row['심도(m)']), align='C', fill=fill)
        pdf.cell(col_widths[4], 8, str(row['너비(m)']), align='C', fill=fill)
        pdf.ln()
        fill = not fill
    
    return bytes(pdf.output())

# ---------------------------------------------------------
# 2. 데이터 생성 함수
# ---------------------------------------------------------
def generate_mock_data(count=20):
    data = []
    current_time = datetime.now()
    
    for i in range(1, count + 1):
        width = round(random.uniform(0.3, 8.0), 2)
        if width > 4.0:
            risk = "긴급"
        elif width > 1.0:
            risk = "우선"
        else:
            risk = "일반"
        
        random_hours = random.randint(0, 48)
        random_minutes = random.randint(0, 59)
        detection_time = current_time - timedelta(hours=random_hours, minutes=random_minutes)

        entry = {
            "index": i,
            "timestamp": detection_time.strftime("%Y-%m-%d %H:%M"),
            "coordinates_3d": {
                "latitude": 37.5665 + random.uniform(-0.02, 0.02),
                "longitude": 126.9780 + random.uniform(-0.03, 0.03),
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
# 3. 메인 앱 UI
# ---------------------------------------------------------
st.set_page_config(page_title="지하 공극 리포트", page_icon="🕳️", layout="wide")
st.title("🕳️ 지하 공극(Sinkhole) 탐지 리포트")

if 'void_data' not in st.session_state:
    st.session_state['void_data'] = generate_mock_data()

if 'address_map' not in st.session_state:
    st.session_state['address_map'] = {}

with st.sidebar:
    st.header("⚙️ 데이터 관리")
    if st.button("🔄 새로운 데이터 생성", use_container_width=True):
        st.session_state['void_data'] = generate_mock_data()
        st.session_state['address_map'] = {} 
        st.success("데이터가 갱신되었습니다!")

data = st.session_state['void_data']

# ---------------------------------------------------------
# 4. 데이터 가공 및 주소 변환
# ---------------------------------------------------------
coords_to_fetch = []
indices_to_fetch = []

for item in data:
    idx = item['index']
    if idx not in st.session_state['address_map']:
        coords_to_fetch.append((item['coordinates_3d']['latitude'], item['coordinates_3d']['longitude']))
        indices_to_fetch.append(idx)

if coords_to_fetch:
    with st.spinner("좌표를 주소로 변환 중입니다... (최초 1회)"):
        fetched_addresses = get_address_batch(coords_to_fetch)
        for i, idx in enumerate(indices_to_fetch):
            st.session_state['address_map'][idx] = fetched_addresses[i]

flattened_data = []
for item in data:
    addr = st.session_state['address_map'].get(item['index'], "변환 중...")
    flattened_data.append({
        "Index": item['index'],
        "탐지 일시": item['timestamp'],
        "주소": addr, 
        "위험도": item['risk_level'],
        "위도": item['coordinates_3d']['latitude'],
        "경도": item['coordinates_3d']['longitude'],
        "심도(m)": item['coordinates_3d']['depth_z'],
        "너비(m)": item['void_size']['width'],
    })
df = pd.DataFrame(flattened_data)

summary = {
    "total": len(df),
    "critical": len(df[df['위험도'] == '긴급']),
    "avg_width": round(df['너비(m)'].mean(), 2)
}

# ---------------------------------------------------------
# 5. 지도 섹션
# ---------------------------------------------------------
st.subheader("🗺️ 탐지 위치 시각화 (Interactive Map)")

col_map, col_detail = st.columns([3, 1])

with col_map:
    center_lat = df['위도'].mean()
    center_lon = df['경도'].mean()

    m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

    for idx, row in df.iterrows():
        if row['위험도'] == '긴급':
            color = 'red'
            icon = 'exclamation-circle'
        elif row['위험도'] == '우선':
            color = 'orange'
            icon = 'exclamation-triangle'
        else:
            color = 'green'
            icon = 'info-circle'
        
        # 팝업에 주소 표시
        popup_html = f"""
        <div style="width:150px">
            <b>#{row['Index']} {row['위험도']}</b><br>
            <span style="font-size:11px">{row['주소']}</span><br>
            <hr style="margin:5px 0">
            크기: {row['너비(m)']}m
        </div>
        """
        
        folium.Marker(
            [row['위도'], row['경도']],
            popup=folium.Popup(popup_html, max_width=200),
            tooltip=f"#{row['Index']} {row['주소'][:10]}...",
            icon=folium.Icon(color=color, icon=icon, prefix='fa'),
        ).add_to(m)

    map_data = st_folium(m, width="100%", height=400, key="main_map")

with col_detail:
    st.markdown("##### 📌 상세 정보")
    selected_void = None

    if map_data and map_data.get("last_object_clicked"):
        clicked_lat = map_data["last_object_clicked"]["lat"]
        clicked_lon = map_data["last_object_clicked"]["lng"]
        
        for _, row in df.iterrows():
            if abs(row['위도'] - clicked_lat) < 0.000001 and abs(row['경도'] - clicked_lon) < 0.000001:
                selected_void = row
                break

    if selected_void is not None:
        st.success(f"**#{int(selected_void['Index'])} {selected_void['위험도']}**")
        st.info(f"📍 **{selected_void['주소']}**")
        
        # [수정됨] 상세 정보에 위도, 경도 다시 추가
        st.write(f"- **위도:** {selected_void['위도']:.6f}")
        st.write(f"- **경도:** {selected_void['경도']:.6f}")
        st.write(f"- **일시:** {selected_void['탐지 일시']}")
        st.write(f"- **심도:** {selected_void['심도(m)']} m")
        st.write(f"- **너비:** {selected_void['너비(m)']} m")
        st.write(f"- **부피:** {round(selected_void['너비(m)'] * selected_void['너비(m)'] * 1.5, 2)} m³ (추정)")
    else:
        st.info("지도에서 핀을 클릭하여 상세 정보를 확인하세요.")

st.divider()

# ---------------------------------------------------------
# 6. 데이터 목록 및 다운로드
# ---------------------------------------------------------
st.subheader("📋 전체 탐지 데이터 목록")

# [수정됨] 목록에서 '주소' 제외하고 '위도', '경도' 추가
cols_for_table = ['Index', '위험도', '위도', '경도', '탐지 일시', '심도(m)', '너비(m)']
st.dataframe(df[cols_for_table], use_container_width=True, height=300)

col_stats, col_download = st.columns([1, 1])

with col_stats:
    st.markdown("##### 📊 요약 통계")
    st.markdown(f"""
    <div style="padding:10px; border-radius:5px; background-color:#f0f2f6; border:1px solid #e6e9ef;">
        <strong>총 발견 수:</strong> {summary['total']}건<br>
        <strong>긴급 조치:</strong> <span style='color:red'>{summary['critical']}건</span> (🔴)<br>
        <strong>평균 너비:</strong> {summary['avg_width']}m
    </div>
    """, unsafe_allow_html=True)

with col_download:
    st.markdown("##### 💾 리포트 다운로드")
    
    # [수정됨] CSV 다운로드 시 '주소' 컬럼 제외 (화면에 보이는 표와 동일하게 설정)
    csv_data = df[cols_for_table].to_csv(index=False).encode('utf-8-sig')
    st.download_button("📄 CSV로 받기", csv_data, "report.csv", "text/csv", use_container_width=True)
    
    st.write("")
    
    try:
        pdf_bytes = generate_pdf_report(df, summary)
        st.download_button(
            label="📥 PDF로 받기",
            data=pdf_bytes,
            file_name="void_report.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary"
        )
    except Exception as e:
        st.error(f"PDF 생성 오류: {e}")
