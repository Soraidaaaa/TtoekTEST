import streamlit as st
import requests
import json
import time
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
from datetime import datetime, timedelta
import urllib.parse

# 페이지 설정
st.set_page_config(
    page_title="🍯 지역 특산품 찾기",
    page_icon="🍯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일링
st.markdown("""
<style>
    .main-header {
        text-align: center;
        background: linear-gradient(90deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    .store-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        background: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .store-name {
        font-size: 1.1rem;
        font-weight: bold;
        color: #333;
    }
    .store-info {
        color: #666;
        font-size: 0.9rem;
        margin: 0.3rem 0;
    }
    .confidence-high {
        background: #d4edda;
        color: #155724;
        padding: 0.2rem 0.5rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .confidence-medium {
        background: #fff3cd;
        color: #856404;
        padding: 0.2rem 0.5rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .confidence-low {
        background: #f8d7da;
        color: #721c24;
        padding: 0.2rem 0.5rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

class LocalProductFinder:
    def __init__(self):
        self.kakao_api_key = None
        self.naver_client_id = None
        self.naver_client_secret = None
        
    def setup_apis(self, kakao_key, naver_id, naver_secret):
        """API 키 설정"""
        self.kakao_api_key = kakao_key
        self.naver_client_id = naver_id
        self.naver_client_secret = naver_secret
        
    def search_places_kakao(self, location, category, size=15):
        """카카오 맵 API로 장소 검색"""
        if not self.kakao_api_key:
            return []
            
        url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        headers = {"Authorization": f"KakaoAK {self.kakao_api_key}"}
        params = {
            "query": f"{location} {category}",
            "size": size
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('documents', [])
        except requests.RequestException as e:
            st.error(f"장소 검색 중 오류 발생: {e}")
            return []
    
    def search_blogs_naver(self, store_name, product, display=10):
        """네이버 블로그 검색 API"""
        if not self.naver_client_id or not self.naver_client_secret:
            return {}
            
        url = "https://openapi.naver.com/v1/search/blog.json"
        headers = {
            "X-Naver-Client-Id": self.naver_client_id,
            "X-Naver-Client-Secret": self.naver_client_secret
        }
        params = {
            "query": f"{store_name} {product}",
            "display": display,
            "sort": "date"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.RequestException as e:
            st.error(f"블로그 검색 중 오류 발생: {e}")
            return {}
    
    def calculate_confidence(self, blog_data, store_name, product):
        """신뢰도 계산"""
        if not blog_data or 'items' not in blog_data:
            return 0.0, "검색 결과 없음"
        
        items = blog_data['items']
        total_count = len(items)
        
        if total_count == 0:
            return 0.0, "관련 블로그 없음"
        
        # 점수 계산 요소들
        product_mentions = 0
        store_mentions = 0
        recent_posts = 0
        
        # 최근 1년 기준
        one_year_ago = datetime.now() - timedelta(days=365)
        
        for item in items:
            title = item.get('title', '').lower()
            description = item.get('description', '').lower()
            
            # HTML 태그 제거
            title = re.sub('<.*?>', '', title)
            description = re.sub('<.*?>', '', description)
            
            # 상품명 언급 확인
            if product.lower() in title or product.lower() in description:
                product_mentions += 1
            
            # 가게명 언급 확인
            if store_name.lower() in title or store_name.lower() in description:
                store_mentions += 1
            
            # 최근 게시물 확인 (날짜 파싱)
            try:
                post_date = datetime.strptime(item.get('postdate', ''), '%Y%m%d')
                if post_date > one_year_ago:
                    recent_posts += 1
            except:
                pass
        
        # 신뢰도 계산 (0-1 범위)
        confidence = 0
        confidence += min(product_mentions / total_count, 1.0) * 0.5  # 상품 언급률 (50%)
        confidence += min(store_mentions / total_count, 1.0) * 0.2    # 가게 언급률 (20%)
        confidence += min(recent_posts / total_count, 1.0) * 0.2      # 최근 게시물 비율 (20%)
        confidence += min(total_count / 10, 1.0) * 0.1               # 전체 게시물 수 (10%)
        
        # 상태 메시지
        if confidence >= 0.7:
            status = f"✅ {product} 판매 가능성 높음"
        elif confidence >= 0.4:
            status = f"⚠️ {product} 판매 가능성 보통"
        else:
            status = f"❓ {product} 판매 정보 부족"
        
        return confidence, status
    
    def create_map(self, places_with_confidence, center_lat=37.5665, center_lng=126.9780):
        """Folium 지도 생성"""
        m = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=12,
            tiles='OpenStreetMap'
        )
        
        for place in places_with_confidence:
            lat = float(place['y'])
            lng = float(place['x'])
            confidence = place['confidence']
            
            # 신뢰도에 따른 마커 색상
            if confidence >= 0.7:
                color = 'green'
                icon = 'star'
            elif confidence >= 0.4:
                color = 'orange'  
                icon = 'info-sign'
            else:
                color = 'red'
                icon = 'question-sign'
            
            # 팝업 내용
            popup_content = f"""
            <div style="width:200px">
                <h4>{place['place_name']}</h4>
                <p><strong>주소:</strong> {place['address_name']}</p>
                <p><strong>전화:</strong> {place.get('phone', '정보없음')}</p>
                <p><strong>신뢰도:</strong> {confidence:.1%}</p>
                <p><strong>상태:</strong> {place['status']}</p>
            </div>
            """
            
            folium.Marker(
                [lat, lng],
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=place['place_name'],
                icon=folium.Icon(color=color, icon=icon)
            ).add_to(m)
        
        return m

# 메인 앱
def main():
    # 헤더
    st.markdown('<h1 class="main-header">🍯 지역 특산품 찾기</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">원하는 특산품을 판매하는 가게를 똑똑하게 찾아보세요!</p>', unsafe_allow_html=True)
    
    # API 키 설정 (Secrets 또는 수동 입력)
    def get_api_keys():
        """Streamlit Secrets 또는 사용자 입력에서 API 키 가져오기"""
        api_keys = {}
        
        # Secrets에서 API 키 가져오기 시도
        try:
            api_keys['kakao'] = st.secrets["api_keys"]["kakao_rest_api"]
            api_keys['naver_id'] = st.secrets["api_keys"]["naver_client_id"]  
            api_keys['naver_secret'] = st.secrets["api_keys"]["naver_client_secret"]
            return api_keys, True
        except:
            # Secrets가 없으면 사용자 입력 받기
            return {}, False
    
    # API 키 확인
    api_keys, has_secrets = get_api_keys()
    
    if has_secrets:
        # Secrets가 있으면 간단한 상태 표시만
        st.sidebar.success("✅ API 키가 자동으로 설정되었습니다")
        st.sidebar.markdown("---")
        st.sidebar.markdown("""
        **🔐 API 키 자동 설정됨**
        - 카카오 REST API
        - 네이버 검색 API
        
        설정을 변경하려면 `.streamlit/secrets.toml` 파일을 수정하세요.
        """)
        
        kakao_api_key = api_keys['kakao']
        naver_client_id = api_keys['naver_id']
        naver_client_secret = api_keys['naver_secret']
        
    else:
        # Secrets가 없으면 사용자 입력 받기
        st.sidebar.title("🔧 API 설정")
        st.sidebar.markdown("### 필요한 API 키를 입력하세요")
        
        kakao_api_key = st.sidebar.text_input(
            "카카오 REST API 키",
            type="password",
            help="https://developers.kakao.com/ 에서 발급받으세요"
        )
        
        naver_client_id = st.sidebar.text_input(
            "네이버 클라이언트 ID",
            help="https://developers.naver.com/ 에서 발급받으세요"
        )
        
        naver_client_secret = st.sidebar.text_input(
            "네이버 클라이언트 시크릿",
            type="password"
        )
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("""
        **💡 자동 설정 방법:**
        1. `.streamlit/secrets.toml` 파일 생성
        2. API 키를 파일에 저장
        3. 다음부터 자동으로 로드됩니다!
        
        **API 발급 방법:**
        - **카카오**: developers.kakao.com
        - **네이버**: developers.naver.com
        """)
        
        # Secrets 파일 설정 도움말
        with st.sidebar.expander("📝 Secrets 설정 도움말"):
            st.code("""
# .streamlit/secrets.toml 파일 생성
[api_keys]
kakao_rest_api = "여기에_카카오_API키"
naver_client_id = "여기에_네이버_클라이언트ID"  
naver_client_secret = "여기에_네이버_시크릿"
            """, language="toml")
    
    # 메인 검색 폼
    col1, col2, col3 = st.columns(3)
    
    with col1:
        location = st.text_input("📍 위치", value="강남구", placeholder="예: 강남구, 홍대")
    
    with col2:
        category = st.selectbox("🏪 카테고리", 
                               ["떡집", "과일가게", "김치가게", "빵집", "한과집", "전통시장"])
    
    with col3:
        product = st.text_input("🛍️ 찾는 상품", value="시루떡", placeholder="예: 시루떡, 사과, 배추김치")
    
    # 검색 버튼
    search_clicked = st.button("🔍 검색하기", type="primary", use_container_width=True)
    
    # API 키 확인
    if not kakao_api_key or not naver_client_id or not naver_client_secret:
        st.warning("⚠️ 사이드바에서 API 키를 모두 입력해주세요.")
        st.info("""
        **데모 실행을 위해 필요한 API:**
        - 카카오 REST API 키 (무료)
        - 네이버 검색 API 클라이언트 ID/Secret (무료)
        """)
        return
    
    # 세션 상태 초기화
    if 'search_results' not in st.session_state:
        st.session_state.search_results = None
    if 'search_params' not in st.session_state:
        st.session_state.search_params = None
    
    # 검색 실행
    if search_clicked and location and product:
        # 검색 파라미터 저장
        current_params = f"{location}_{category}_{product}"
        
        # 새로운 검색인지 확인
        if st.session_state.search_params != current_params:
            st.session_state.search_params = current_params
            
            finder = LocalProductFinder()
            finder.setup_apis(kakao_api_key, naver_client_id, naver_client_secret)
            
            with st.spinner("🔍 주변 가게를 검색하고 있습니다..."):
                # 1단계: 장소 검색
                places = finder.search_places_kakao(location, category)
                
                if not places:
                    st.error("검색 결과가 없습니다. 위치나 카테고리를 다시 확인해주세요.")
                    st.session_state.search_results = None
                    return
                
                st.success(f"📍 {len(places)}개의 {category}을(를) 찾았습니다!")
            
            # 2단계: 블로그 검색 및 신뢰도 계산
            progress_container = st.container()
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                places_with_confidence = []
                
                for i, place in enumerate(places):
                    status_text.text(f"📝 {place['place_name']}의 {product} 판매 정보를 확인 중... ({i+1}/{len(places)})")
                    
                    # 블로그 검색
                    blog_data = finder.search_blogs_naver(place['place_name'], product)
                    time.sleep(0.1)  # API 호출 제한 방지
                    
                    # 신뢰도 계산
                    confidence, status = finder.calculate_confidence(
                        blog_data, place['place_name'], product
                    )
                    
                    place['confidence'] = confidence
                    place['status'] = status
                    place['blog_count'] = len(blog_data.get('items', []))
                    
                    places_with_confidence.append(place)
                    progress_bar.progress((i + 1) / len(places))
                
                # 신뢰도순 정렬
                places_with_confidence.sort(key=lambda x: x['confidence'], reverse=True)
                
                # 검색 결과를 세션 상태에 저장
                st.session_state.search_results = places_with_confidence
                
                # 진행률 표시 정리
                progress_bar.empty()
                status_text.success(f"✅ 검색 완료! {len(places_with_confidence)}개 가게의 {product} 판매 정보를 확인했습니다.")
        
    # 검색 결과 표시 (세션 상태에서 가져옴)
    if st.session_state.search_results is not None:
        places_with_confidence = st.session_state.search_results
        
        # 결과 표시
        st.markdown(f"## 🎯 '{product}' 검색 결과")
        
        # 요약 정보
        high_conf = len([p for p in places_with_confidence if p['confidence'] >= 0.7])
        medium_conf = len([p for p in places_with_confidence if p['confidence'] >= 0.4])
        
        col_summary1, col_summary2, col_summary3 = st.columns(3)
        with col_summary1:
            st.metric("총 가게 수", len(places_with_confidence))
        with col_summary2:
            st.metric("판매 확실", f"{high_conf}개", delta="높은 신뢰도")
        with col_summary3:
            st.metric("판매 가능", f"{medium_conf}개", delta="보통 이상 신뢰도")
        
        # 탭으로 구분하여 표시
        tab1, tab2, tab3 = st.tabs(["🗺️ 지도 보기", "📋 상세 결과", "📊 데이터 표"])
        
        with tab1:
            st.markdown("### 📍 지도에서 보기")
            # 중심점 계산 (첫 번째 결과 기준)
            if places_with_confidence:
                center_lat = float(places_with_confidence[0]['y'])
                center_lng = float(places_with_confidence[0]['x'])
                
                map_obj = finder.create_map(places_with_confidence, center_lat, center_lng)
                st_folium(map_obj, width=700, height=500, returned_objects=["last_object_clicked"])
        
        with tab2:
            st.markdown("### 📋 상세 결과")
            
            # 신뢰도별 필터링
            filter_confidence = st.selectbox(
                "신뢰도 필터링",
                ["전체", "높음 (70% 이상)", "보통 (40% 이상)", "낮음 (40% 미만)"],
                key="confidence_filter"
            )
            
            # 필터링 적용
            filtered_places = places_with_confidence
            if filter_confidence == "높음 (70% 이상)":
                filtered_places = [p for p in places_with_confidence if p['confidence'] >= 0.7]
            elif filter_confidence == "보통 (40% 이상)":
                filtered_places = [p for p in places_with_confidence if p['confidence'] >= 0.4]
            elif filter_confidence == "낮음 (40% 미만)":
                filtered_places = [p for p in places_with_confidence if p['confidence'] < 0.4]
            
            if not filtered_places:
                st.info("선택한 조건에 맞는 결과가 없습니다.")
            else:
                # LocalProductFinder 인스턴스가 필요한 경우를 대비
                if 'finder' not in locals():
                    finder = LocalProductFinder()
                    
                for i, place in enumerate(filtered_places):
                    confidence = place['confidence']
                    
                    # 신뢰도에 따른 스타일 클래스
                    if confidence >= 0.7:
                        confidence_class = "confidence-high"
                    elif confidence >= 0.4:
                        confidence_class = "confidence-medium"
                    else:
                        confidence_class = "confidence-low"
                    
                    with st.container():
                        st.markdown(f"""
                        <div class="store-card">
                            <div class="store-name">{i+1}. {place['place_name']}</div>
                            <div class="store-info">📍 {place['address_name']}</div>
                            <div class="store-info">📞 {place.get('phone', '전화번호 정보 없음')}</div>
                            <div class="store-info">📝 블로그 언급 {place['blog_count']}회</div>
                            <span class="{confidence_class}">신뢰도 {confidence:.1%}</span>
                            <div class="store-info" style="margin-top: 0.5rem;">{place['status']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 가게별 추가 정보 (expander)
                        with st.expander(f"{place['place_name']} 더보기"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**카테고리:** {place.get('category_name', '정보없음')}")
                                st.write(f"**도로명주소:** {place.get('road_address_name', '정보없음')}")
                            with col2:
                                st.write(f"**거리:** {place.get('distance', '정보없음')}m")
                                if place.get('place_url'):
                                    st.write(f"**상세정보:** [카카오맵에서 보기]({place['place_url']})")
                                    
        with tab3:
            st.markdown("### 📊 상세 데이터")
            # LocalProductFinder 인스턴스가 필요한 경우를 대비
            if 'finder' not in locals():
                finder = LocalProductFinder()
                
            # 결과 데이터프레임
            df = pd.DataFrame([
                {
                    '순위': i + 1,
                    '가게명': place['place_name'],
                    '주소': place['address_name'],
                    '전화번호': place.get('phone', '정보없음'),
                    '블로그 언급': f"{place['blog_count']}회",
                    '신뢰도': f"{place['confidence']:.1%}",
                    '상태': place['status'].replace('✅', '').replace('⚠️', '').replace('❓', '').strip()
                }
                for i, place in enumerate(places_with_confidence)
            ])
            
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "순위": st.column_config.NumberColumn(width="small"),
                    "신뢰도": st.column_config.ProgressColumn(
                        width="medium",
                        min_value=0,
                        max_value=1,
                        format="%.1f%%"
                    )
                }
            )
            
            # CSV 다운로드
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 결과를 CSV로 다운로드",
                data=csv,
                file_name=f"{location}_{category}_{product}_검색결과_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="download_csv"
            )
    
    elif search_clicked:
        st.info("검색 조건을 확인해주세요.")

if __name__ == "__main__":
    main()