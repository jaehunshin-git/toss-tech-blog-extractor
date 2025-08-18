# 토스가 꿈꾸는 React Native 기술의 미래

**Date:** 2024년 3월 25일
**URL:** https://toss.tech/article/react-native-2024

---

안녕하세요, 토스 프론트엔드 엔지니어링 헤드 박서진입니다.

토스에서는 최고의 사용자 경험이 필요한 곳은 Native, 매일매일 실험으로 제품을 개선하는 제품은 React Native/WebView로 구성하고 있어요.

토스 프론트엔드 챕터는 지난 2022년 6월부터 React Native 기술에 투자하고 있는데요. 이번 기술 블로그 아티클에서는 왜 React Native를 고려하고 있는지, 현재 어느 정도까지 사용하고 있는지, 그리고 앞으로의 계획이 어떻게 되는지에 대해서 소개드리려고 합니다.

## 왜 React Native인가

토스는 React Native로 매끄러운 사용자 경험과 높은 개발 생산성을 제공하여, 모바일 서비스를 만드는 새로운 표준을 제시하고자 해요.

React Native로 서비스를 개발하면, WebView로 서비스를 만들 때보다 사용자 경험을 크게 개선할 수 있어요. React Native는 기본적으로 파일 시스템에서 JavaScript 파일을 읽어오기 때문에, WebView와 다르게 네트워크로 인한 로딩 속도를 없앨 수 있기 때문이죠.

한국처럼 대부분의 사용자가 2020년 이후에 출시한 최신 핸드폰을 쓰는 환경에서는, JavaScript 실행도 매우 빨라요. 토스에서 “매일 방문 미션” 제품을 React Native로 만들었을 때, 1초 이상의 로딩 속도를 감축시킬 수 있었어요. 

특히 앞으로 모바일 기기 성능 발전과 더불어서 JavaScript 실행 속도는 매년 두 자릿수 퍼센티지로 빨라지고, 로딩 시간은 그만큼 계속 줄어들 것으로 보여요. [Hermes 엔진](https://hermesengine.dev/)으로 JavaScript를 미리 컴파일하면 초기 로딩 속도를 더 빠르게 할 수도 있답니다. \([사진 출처](https://engineering.fb.com/2019/07/12/android/hermes/)\)

프론트엔드 개발자의 개발 생산성도 개선할 수 있는데요. 

먼저, WebView에서 생산성을 깎는 다양한 문제를 근본적으로 해결할 수 있었어요. 토스는 모바일 서비스를 WebView로 만들면서, 여러 제약이 있다는 것을 알게 되었어요. iOS에서는 `display: fixed`와 `autoFocus` 문제가 있었고, Android는 WebView 버전마다 웹 서비스가 다르게 동작하기도 했죠. History도 마음껏 수정하기 어려웠습니다. React Native는 Native 렌더러를 사용하고, 높은 자유도를 제공하기 때문에, 이 문제를 모두 깔끔히 해결할 수 있었어요.

또한, 빌드와 배포 속도를 개선할 수 있었어요. 보통 WebView 기반으로 서비스를 만들면 빌드가 느리다는 문제에 맞닥뜨리게 되어요. SSR을 쓰는 경우 서버를 빌드하고 배포하는 시간이 필요하죠. 반면, React Native 기술에서는 배포 단계가 단순해서, 정적인 JavaScript 파일 1개만 빌드하고 업로드하면 돼요. 그래서 배포가 완료되기까지의 시간을 손쉽게 최적화할 수 있죠.

마지막으로, 코드의 복잡도도 낮출 수 있었어요. 토스는 100개 넘는 Server-side rendering \(SSR\) 서비스를 운영하고 있는데요. SSR을 이용하면 기존의 [Client-side rendering 접근보다 로딩 속도를 크게 개선하지만](https://www.youtube.com/watch?v=IKyA8BKxpXc), Server와 Client를 넘나드는 Universal한 코드를 작성해야 해요. 두 환경을 모두 고려해야 하기 때문에, 코드의 복잡도가 크게 올라갔죠. 반면, React Native를 이용하면 Client에서 실행되는 경우만 고려하면 되었어요.

토스에서는 사용자 경험과 개발 생산성의 두 가지 가치가 제일 중요한데요. 이렇게 React Native를 이용하면 사용자에게는 더 좋은 경험을 제공하면서도, 개발 생산성도 높일 수 있겠다는 생각이 들었어요.

## 토스 React Native 기술의 현재

토스 프론트엔드 챕터에서는 지난 1년 6개월간 React Native 화면을 조심스럽게 확대해 나가면서, 실제로 토스에서 가치를 제공하는지 확인했어요.

토스에서 “혜택 탭”은 React Native로 운영된 첫 번째 서비스로서, 토스에서 광고를 보고 앱테크로 돈을 버는 새로운 표준을 제시했습니다. 매출도 크게 증가했죠. 로딩 속도를 1초 이상 감축했고, 자동 동영상 재생과 같이 기존의 WebView에서 어려웠던 부분을 깔끔히 해결할 수 있었습니다.

혜택 탭 외로도, 지난 1년간 토스에서는 React Native 서비스를 다수 신규 런칭했어요. “피드 보고 포인트 받기”, “매일 방문 미션”과 같은 다양한 제품이 개발되어 서비스되고 있죠. 덕분에 지금은 React Native 뷰는 WebView를 이용한 화면보다도 많이 실행되고 있어요.

2024년 토스는 React Native를 서비스를 만들어 나가는 정식 기술 가운데 하나로 사용해보기로 하고, 서비스를 확대해 나가는 단계예요.

## React Native 개발환경 자세히 살펴보기

그렇다면 토스에서는 어떻게 React Native 개발환경을 만들어나가고 있을까요?

### 마이크로 프론트엔드 아키텍처

토스에서는 사일로와 서비스마다 독립적으로 서비스를 운영하는 것이 매우 중요해요. 토스는 DRI 문화를 핵심 원칙으로 삼고 있기 때문에, 사일로에서 자체적으로 빠르게 의사결정을 내려서 배포 주기와 방법을 결정해야 하기 때문이죠. 한 서비스의 변경사항이 다른 서비스에게 영향을 주어서도 안 됩니다.

일반적으로 React Native 애플리케이션은 모놀리식한 단일 파일로 구성되는 경우가 많은데요. 토스에서는 자체적으로 React Native 애플리케이션을 마이크로 프론트엔드 아키텍처로 관리하는 시스템을 만들었습니다.

토스에서는 서비스마다 React Native 뷰가 나누어져 있으며, 각 서비스 화면은 독립적으로 실행되어 다른 화면에 영향을 주지 않습니다. 서비스가 실행될 때, 필요한 JavaScript 파일만 동적으로 로드해서 실행하는 형태예요. 

구체적으로는, 토스에서는 React Native 뷰를 그리기 위해 “Shared 번들” 과 “Service 번들”을 나누어 차례대로 실행합니다. “Shared 번들”은 `react-native` 라이브러리와 같이, 네이티브 영역과 강하게 연결되어 있어, 모든 서비스가 공통으로 사용하는 코드입니다. 그리고 “Service 번들”은 각 서비스에서 다르게 운영하는 부분만 별도로 분리된 코드에요. 두 코드는 서비스가 실행될 때 순서대로 동적으로 로드돼요. 이로써 사용자들은 서비스를 띄울 때 필요한 만큼만의 작은 JavaScript 코드를 실행하게 됩니다.

이렇게 만들어진 “Shared 번들” 과 “Service 번들” 은 토스의 React Native 플랫폼 팀이 만든 자체적인 어드민을 이용해서 CDN으로 배포돼요. 그리고 서비스 개발자는 간편한 UI로, 1초만에 React Native 화면을 배포하면 되죠.

1~100% 사이에서 일부 사용자들에게 원하는 만큼 카나리 배포를 할 수도 있고, 나만 보는 배포를 쉽게 만들 수도 있답니다.

### ESBuild를 이용한 신속한 배포

토스에서는 React Native 번들을 빌드하기 위해 Metro 대신 ESBuild 번들러를 사용하고 있어요. Metro 번들러는 빌드하는 데에 시간이 오래 걸리고, Tree-shaking을 지원하지 않으며, 캐시를 리셋하지 않으면 일관적인 동작을 보장하기 어렵기 때문이었습니다. 

ESBuild를 도입한 이후에, 빌드 시간을 1분 안쪽으로 줄일 수 있었어요. 번들에서 안 쓰는 코드를 Tree-shaking으로 삭제해서, 번들 사이즈도 크게 감축시켰죠.

자세한 내용은 2023년 FEConf에서 “[React Native, Metro를 넘어서](https://www.youtube.com/watch?v=QfU5REp8sjQ)” 발표에서 확인하실 수 있어요.

## React Native의 미래

토스 프론트엔드 챕터는 React Native 기술의 미래가 밝다고 생각해요. 과거 React Native 기술에 대한 인식이 좋지 않았을 때도 있었지만, React Native 커뮤니티가 지속적으로 유의미한 발전을 만들고 있다고 보고 있습니다.

먼저, React Native 애플리케이션은 시간이 갈수록 자연스럽게 빨라지고 있어요. 스마트폰이 JavaScript를 실행하는 속도가 계속 빨라지고 있기 때문이죠. 하나의 예시로, 유명한 채팅 앱인 [Discord는 iOS와 Android 모두 React Native로 구성](https://discord.com/blog/why-discord-is-sticking-with-react-native)되어 있는데요. 놀라울 정도로 빠른 성능과 아름다운 사용성을 보여주고 있어요. 그 외로 Microsoft가 제공하는 Office 앱이나, Shopify, Amazon 같은 사례도 있답니다. 

최근 Meta에서는 [react-strict-dom \(RSD\)](https://github.com/facebook/react-strict-dom) 이라고 하는 오픈소스 프로젝트를 발표했는데요. 하나의 코드베이스로 React와 React Native를 연결하려고 하는 비전을 제시하고 있어요. 마찬가지로 토스에서도 Web과 React Native에서 모두 아름답고 안정적으로 동작하는 “Isomorphic Package” 을 만들어 나가려고 해요.

Meta가 공개한 또다른 오픈소스 프로젝트로는 [Static Hermes](https://www.youtube.com/watch?v=q-xKYA0EO-c)가 있어요. JavaScript를 바이너리로 컴파일함으로써 실행 속도를 네이티브와 동일한 수준으로 맞추려는 담대한 목표를 가지고 있죠. 

또한, 2024년 [React Conf](https://conf.react.dev/)는 Meta와 React Native 전문 오픈소스 회사 [Callstack](https://www.callstack.com/)이 협업해서 열리는데요. 아직 자세한 발표 내용이 공개되지는 않았지만, React Native를 주제로 하는 발표가 다수 예정되어 있어요. React Native는 앞으로 React Server Components와 함께 React 커뮤니티의 가장 중심적인 주제 중 하나가 될 것이라고 생각해요.

## 토스의 React Native Platform Team에서 일하기

토스에는 React Native Platform Team이 있어요. 프론트엔드 플랫폼 개발자 3명과 iOS 개발자 1명으로 구성되어 있고, 지금은 Android 개발자를 찾고 있어요. 

모든 팀원이 각자의 분야에 대한 전문가로 구성되어 있어요. [이근혁](https://github.com/leegeunhyeok)님은 React Native를 ESBuild로 빌드하는 [react-native-esbuild](https://github.com/leegeunhyeok/react-native-esbuild) 프로젝트를 오픈소스화하고 토스에 합류하셨어요. 오진성님은 iOS 분야의 전문가로, [Cocoapods 없이 React Native를 앱에 포함하는 구조를 설계하셨죠](https://toss.tech/article/react-native-without-cocoapods). 기술적인 배경은 다르지만, 모두가 본인의 주된 개발 언어에 관계없이 주도적이고 열정적으로 프로젝트에 참여하고 있어요.

React Native Platform Team의 특징이라고 한다면, 모두가 전문 분야에 관계없이 JavaScript, iOS, Android 모든 영역을 담당하는 것을 지향한다는 점이에요. 프론트엔드 개발자도 iOS, Android 영역에 기여하고, 네이티브 개발자도 JavaScript 영역에 기여하려고 하죠. 프론트엔드와 네이티브 개발자가 다양한 도메인에 소프트랜딩할 수 있도록, 서로가 서로를 온보딩하고, 매일같이 모여서 짝 프로그래밍을 하는 문화를 가지고 있어요. 모두가 iOS, Android, JavaScript 등 클라이언트 개발 전반에 대한 전문성을 확보하려고 하고 있습니다.

대표적인 예시로, iOS 개발자도 React Native의 TDS\(디자인 시스템\) 라이브러리에 기여하고 있고, 프론트엔드 개발자도 iOS, Android의 React Native 모듈 유지보수에 참여하여 PR을 올리고 있어요.

React Native는 iOS와 Android, JavaScript 개발환경에 대한 이해가 없으면 다루기 힘든 기술인데요. 토스에는 국내 최고 수준으로 JavaScript, iOS, Android를 다루는 엔지니어들이 모여 있어요. 덕분에 어려운 문제를 맞닥뜨렸다고 하더라도, 각 플랫폼의 전문가와 함께 토론하면서 배워가고, 해결할 수 있죠. 치열하게 고민하며 최고의 개발환경을 만들어 나가는 짜릿함을 느끼고 있어요.

이렇게 토스의 React Native Platform Team은, 쫀득한 사용자 경험과 슬릭한 개발 생산성 모두를 제공하는 개발환경을 주도적으로 만들어 나갈 예정이에요.

무엇보다, 토스의 React Native 플랫폼은 여기에 그치지 않고, 올해 안에 지금까지 만든 React Native 배포 모듈과 AWS 인프라를 오픈소스화하고, 세계적으로 앱을 만들어 나가는 Best Practice를 제시하는 것이 목표예요.

최고의 개발환경에서 React Native 서비스를 만들어 나가고 싶으신가요? [Frontend Developer](https://toss.im/career/job-detail?job_id=4071101003)로 합류하시면, 토스의 React Native 개발환경을 경험할 수 있답니다.

React Native Platform Team에서 개발환경을 가꾸어 나가는 여정에 함께하고 싶으신가요? [Frontend Platform Engineer](https://toss.im/career/job-detail?job_id=4071101003&detailedPosition=Platform)나 [Android Developer \(React Native\)](https://toss.im/career/job-detail?job_id=5924470003) 에 지원하시면 팀에 합류하실 수 있어요.

그러면 앞으로 토스가 보여줄 React Native 개발환경을 기대해주세요\!