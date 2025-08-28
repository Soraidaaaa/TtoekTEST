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
    
    # 사이드바 - API 설정
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
    **API 발급 방법:**
    1. **카카오**: developers.kakao.com → 앱 생성 → REST API 키 복사
    2. **네이버**: developers.naver.com → 애플리케이션 등록 → 검색 API 추가
    """)
    
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
    
    # 검색 실행
    if search_clicked and location and product:
        finder = LocalProductFinder()
        finder.setup_apis(kakao_api_key, naver_client_id, naver_client_secret)
        
        with st.spinner("🔍 주변 가게를 검색하고 있습니다..."):
            # 1단계: 장소 검색
            places = finder.search_places_kakao(location, category)
            
            if not places:
                st.error("검색 결과가 없습니다. 위치나 카테고리를 다시 확인해주세요.")
                return
            
            st.success(f"📍 {len(places)}개의 {category}을(를) 찾았습니다!")
        
        # 2단계: 블로그 검색 및 신뢰도 계산
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        places_with_confidence = []
        
        for i, place in enumerate(places):
            status_text.text(f"📝 {place['place_name']}의 {product} 판매 정보를 확인 중...")
            
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
        
        status_text.empty()
        progress_bar.empty()
        
        # 결과 표시
        st.markdown(f"## 🎯 '{product}' 검색 결과")
        
        # 지도와 결과 리스트를 나란히 표시
        col_map, col_results = st.columns([1, 1])
        
        with col_map:
            st.markdown("### 📍 지도에서 보기")
            # 중심점 계산 (첫 번째 결과 기준)
            if places_with_confidence:
                center_lat = float(places_with_confidence[0]['y'])
                center_lng = float(places_with_confidence[0]['x'])
                
                map_obj = finder.create_map(places_with_confidence, center_lat, center_lng)
                st_folium(map_obj, width=500, height=400)
        
        with col_results:
            st.markdown("### 📋 상세 결과")
            
            for place in places_with_confidence:
                confidence = place['confidence']
                
                # 신뢰도에 따른 스타일 클래스
                if confidence >= 0.7:
                    confidence_class = "confidence-high"
                elif confidence >= 0.4:
                    confidence_class = "confidence-medium"
                else:
                    confidence_class = "confidence-low"
                
                st.markdown(f"""
                <div class="store-card">
                    <div class="store-name">{place['place_name']}</div>
                    <div class="store-info">📍 {place['address_name']}</div>
                    <div class="store-info">📞 {place.get('phone', '전화번호 정보 없음')}</div>
                    <div class="store-info">📝 블로그 언급 {place['blog_count']}회</div>
                    <span class="{confidence_class}">신뢰도 {confidence:.1%}</span>
                    <div class="store-info" style="margin-top: 0.5rem;">{place['status']}</div>
                </div>
                """, unsafe_allow_html=True)
        
        # 결과 데이터프레임
        st.markdown("### 📊 상세 데이터")
        df = pd.DataFrame([
            {
                '가게명': place['place_name'],
                '주소': place['address_name'],
                '전화번호': place.get('phone', '정보없음'),
                '블로그 언급': f"{place['blog_count']}회",
                '신뢰도': f"{place['confidence']:.1%}",
                '상태': place['status']
            }
            for place in places_with_confidence
        ])
        
        st.dataframe(df, use_container_width=True)
        
        # CSV 다운로드
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 결과를 CSV로 다운로드",
            data=csv,
            file_name=f"{location}_{category}_{product}_검색결과.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()