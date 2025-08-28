# 🍯 지역 특산품 찾기

원하는 특산품을 판매하는 가게를 똑똑하게 찾아주는 웹 애플리케이션입니다.

## 🚀 주요 기능

- **위치 기반 가게 검색**: 카카오 맵 API를 사용하여 주변 가게를 찾습니다
- **스마트 상품 검증**: 네이버 블로그 검색을 통해 특정 상품 판매 여부를 확인합니다
- **신뢰도 계산**: 블로그 언급 빈도, 최신성 등을 종합하여 판매 가능성을 점수화합니다
- **지도 시각화**: 검색 결과를 지도에 마커로 표시합니다
- **결과 다운로드**: 검색 결과를 CSV 파일로 저장할 수 있습니다

## 📋 필요한 API

### 1. 카카오 REST API 키
1. [카카오 개발자센터](https://developers.kakao.com/) 접속
2. 애플리케이션 등록
3. "앱 키" > "REST API 키" 복사

### 2. 네이버 검색 API
1. [네이버 개발자센터](https://developers.naver.com/) 접속
2. "Application > 애플리케이션 등록" 클릭
3. "검색" API 추가
4. Client ID와 Client Secret 복사

## 🛠️ 설치 및 실행

### 로컬 실행
```bash
# 저장소 클론
git clone <your-repo-url>
cd local-product-finder

# 패키지 설치
pip install -r requirements.txt

# 앱 실행
streamlit run app.py
```

### Streamlit Cloud 배포
1. GitHub에 코드 업로드
2. [Streamlit Cloud](https://share.streamlit.io/) 접속
3. "New app" > GitHub 저장소 연결
4. 자동 배포 완료

### Heroku 배포
```bash
# Heroku CLI 설치 후
heroku create your-app-name
git push heroku main
```

## 📁 프로젝트 구조

```
local-product-finder/
├── app.py              # 메인 애플리케이션
├── requirements.txt    # Python 패키지 의존성
├── README.md          # 프로젝트 설명서
└── .streamlit/
    └── config.toml    # Streamlit 설정 (선택사항)
```

## 🔧 사용 방법

1. **API 키 입력**: 사이드바에서 카카오와 네이버 API 키를 입력합니다
2. **검색 조건 설정**: 위치, 카테고리, 찾는 상품을 입력합니다
3. **검색 실행**: "검색하기" 버튼을 클릭합니다
4. **결과 확인**: 지도와 리스트에서 결과를 확인합니다

## 📊 신뢰도 계산 방식

- **상품 언급률** (50%): 블로그에서 해당 상품이 언급된 비율
- **가게 언급률** (20%): 블로그에서 가게명이 언급된 비율  
- **최근 게시물** (20%): 1년 내 작성된 게시물 비율
- **전체 언급량** (10%): 총 블로그 언급 횟수

## 🚦 API 사용량 제한

- **카카오 맵 API**: 일 300,000회 (무료)
- **네이버 검색 API**: 일 25,000회 (무료)

## 🎯 활용 예시

- **시루떡을 파는 떡집 찾기**: "강남구" + "떡집" + "시루떡"
- **홍로 사과를 파는 과일가게**: "홍대" + "과일가게" + "홍로"
- **수제 김치를 파는 가게**: "이태원" + "김치가게" + "수제김치"

## 🤝 기여하기

1. Fork 생성
2. Feature 브랜치 생성 (`git checkout -b feature/AmazingFeature`)
3. 변경사항 커밋 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치에 Push (`git push origin feature/AmazingFeature`)
5. Pull Request 생성

## 📄 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

## 🔮 향후 계획

- [ ] 이미지 검색을 통한 상품 확인 정확도 향상
- [ ] 사용자 리뷰 기능 추가
- [ ] 실시간 재고 정보 연동
- [ ] 모바일 앱 버전 개발
- [ ] 다국어 지원 (영어, 일본어)

## 🐛 문제 해결

### 자주 발생하는 오류
- **API 키 오류**: API 키가 올바른지 확인하고 권한 설정을 점검하세요
- **검색 결과 없음**: 위치명을 좀 더 구체적으로 입력해보세요
- **느린 응답**: API 호출량이 많을 때 발생할 수 있습니다

### 문의사항
이슈가 있으시면 GitHub Issues에 남겨주세요.