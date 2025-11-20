import streamlit as st
import pandas as pd
import random
import io
import os
import urllib.request
from fpdf import FPDF
import folium
from streamlit_folium import st_folium

# ---------------------------------------------------------
# 0. 한글 폰트 자동 설정 (PDF용)
# ---------------------------------------------------------
def get_korean_font():
    font_path = "NanumGothic.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        try:
            urllib.request.urlretrieve(url, font_path)
        except:
            st.error("폰트 다운로드 실패. PDF에서 한글이 깨질 수 있습니다.")
    return font_path

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
    col_widths = [15, 20, 35, 35, 35, 30] 
    headers = ['Index', '위험도', '위도', '경도', '심도(m)', '너비(m)']
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 10, h, align='C', fill=True)
    pdf.ln()

    pdf.set_text_color(0, 0, 0)
    pdf.set_font('NanumGothic', '', 9)
    fill = False 
    for index, row in df.iterrows():
        if row['위험도'] == '긴급':
            pdf.set_text_color(192, 57, 43)
        else:
            pdf.set_text_color(0, 0, 0)
        pdf.set_fill_color(245, 245, 245)
        
        pdf.cell(col_widths[0], 8, str(row['Index']), align='C', fill=fill)
        pdf.cell(col_widths[1], 8, str(row['위험도']), align='C', fill=fill)
        pdf.cell(col_widths[2], 8, str(row['위도']), align='C', fill=fill)
        pdf.cell(col_widths[3], 8, str(row['경도']), align='C', fill=fill)
        pdf.cell(col_widths[4], 8, str(row['심도(m)']), align='C', fill=fill)
        pdf.cell(col_widths[5], 8, str(row['너비(m)']), align='C', fill=fill)
        pdf.ln()
        fill = not fill
    return pdf.output()

# ---------------------------------------------------------
# 2. 데이터 생성 함수
# ---------------------------------------------------------
def generate_mock_data(count=20):
    data = []
    for i in range(1, count + 1):
        width = round(random.uniform(0.3, 8.0), 2)
        if width > 4.0:
            risk = "긴급"
        elif width > 1.0:
            risk = "우선"
        else:
            risk = "일반"

        entry = {
            "index": i,
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
# 3. 메인 앱 UI 및 데이터 처리
# ---------------------------------------------------------
st.set_page_config(page_title="지하 공극 리포트", page_icon="🕳️", layout="wide")
st.title("🕳️ 지하 공극(Sinkhole) 탐지 리포트")

if 'void_data' not in st.session_state:
    st.session_state['void_data'] = generate_mock_data()

with st.sidebar:
    st.header("⚙️ 설정")
    if st.button("🔄 새로운 데이터 생성", use_container_width=True):
        st.session_state['void_data'] = generate_mock_data()
        st.success("데이터가 갱신되었습니다!")

data = st.session_state['void_data']

# 데이터 가공
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
df = pd.DataFrame(flattened_data)

summary = {
    "total": len(df),
    "critical": len(df[df['위험도'] == '긴급']),
    "avg_width": round(df['너비(m)'].mean(), 2)
}

# ---------------------------------------------------------
# 4. 지도 섹션 (높이 조절 및 공백 최소화)
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
        
        popup_html = f"""
        <b>Index: {row['Index']}</b><br>
        위험도: {row['위험도']}<br>
        크기: {row['너비(m)']}m<br>
        심도: {row['심도(m)']}m
        """
        
        folium.Marker(
            [row['위도'], row['경도']],
            popup=folium.Popup(popup_html, max_width=200),
            tooltip=f"탐지 #{row['Index']} ({row['위험도']})",
            icon=folium.Icon(color=color, icon=icon, prefix='fa'),
        ).add_to(m)

    # [수정됨] 지도 높이를 500 -> 400으로 줄여서 공백을 줄임
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
        st.success(f"**선택된 공극: #{int(selected_void['Index'])}**")
        st.write(f"- **위험도:** {selected_void['위험도']}")
        st.write(f"- **위도:** {selected_void['위도']}")
        st.write(f"- **경도:** {selected_void['경도']}")
        st.write(f"- **심도:** {selected_void['심도(m)']} m")
        st.write(f"- **너비:** {selected_void['너비(m)']} m")
    else:
        st.info("지도에서 핀을 클릭해주세요.")

st.divider()

# ---------------------------------------------------------
# 5. 데이터 목록 및 다운로드 (오류 수정됨)
# ---------------------------------------------------------
st.subheader("📋 전체 탐지 데이터 목록")
st.dataframe(df, use_container_width=True, height=300)

col_stats, col_download = st.columns([1, 1])

with col_stats:
    st.markdown("##### 📊 요약 통계")
    # [수정됨] st.info 오류 해결 -> st.markdown 사용
    # HTML을 사용하기 위해 st.markdown으로 변경하고 스타일을 직접 적용했습니다.
    st.markdown(f"""
    <div style="padding:10px; border-radius:5px; background-color:#f0f2f6; border:1px solid #e6e9ef;">
        <strong>총 발견 수:</strong> {summary['total']}건<br>
        <strong>긴급 조치:</strong> <span style='color:red'>{summary['critical']}건</span> (🔴)<br>
        <strong>평균 너비:</strong> {summary['avg_width']}m
    </div>
    """, unsafe_allow_html=True)

with col_download:
    st.markdown("##### 💾 리포트 다운로드")
    csv_data = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📄 CSV로 받기", csv_data, "report.csv", "text/csv", use_container_width=True)
    
    st.write("") 
    if st.button("📕 PDF 리포트 생성", type="primary", use_container_width=True):
        with st.spinner('PDF 생성 중...'):
            try:
                pdf_bytes = generate_pdf_report(df, summary)
                st.download_button("📥 PDF 다운로드", bytes(pdf_bytes), "void_report.pdf", "application/pdf", use_container_width=True, key="pdf-download-2")
                st.success("완료!")
            except Exception as e:
                st.error(f"오류: {e}")
