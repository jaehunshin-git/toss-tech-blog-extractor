# 조금만 신경써서 초기 렌더링 빠르게 하기 (feat. JAM Stack)

**Date:** 2022년 2월 9일
**URL:** https://toss.tech/article/faster-initial-rendering

---

## 들어가면서

SPA\(Single Page Application\) 구조로 웹 프론트엔드 애플리케이션이 개발되면서 초기 렌더링 속도는 프런트엔드 개발자에게 중요한 과제 중 하나가 되었습니다. 사용자 경험에 영향을 줄 수 있는 가장 큰 요소 중 하나가 바로 속도이기 때문입니다. 이번 개선은 [Web Vitals](https://web.dev/vitals/) 지표를 중심으로 측정했습니다.

## 주어진 과제들

### 과제 1. 번들 사이즈

애플리케이션에 기능이 추가되면서 번들 사이즈가 커졌고 이로 인해 초기 렌더링이 늦어지는 문제가 발생하게 됩니다. 네트워크 비용을 줄이기 위해 Webpack으로 번들링했던 소스코드를 다시 적절한 단위로 코드 스플리팅\(Code Splitting\)을 하기도 하고 사용되지 않는 코드, 불필요한 코드들을 덜어내기 위한 트리 세이킹\(Tree Shaking\)을 위한 작업을 하기도 합니다.

→ [\[SLASH 21\] 이한 – JavaScript Bundle Diet](https://www.youtube.com/watch?v=EP7g5R-7zwM)

이러한 노력을 하더라도 개선할 수 있는 부분엔 한계가 존재했습니다. 초기에 렌더링되는 index.html 자체가 비어있는 문서\(Document\)이기 때문에 스크립트가 실행되어 실제로 렌더링이 되기까지의 시간이 존재하기 때문입니다.

### 과제 2. 렌더링 시점

그렇다면 이제 렌더링 시점을 어떻게 앞당길 것인가에 대한 문제를 해결해야 됩니다. 사용자가 [tosspayments.com](http://tosspayments.com/) 에 접근했을 때, 사용자가 최종적으로 볼 수 있는 화면을 서버에서 미리 그리고 그 화면을 브라우저에 전달해주면 초기 렌더링 시점이 앞당겨지지 않을까요?

물론 인터랙션이 가능해지기 까지는 하이드레이트\(Hydrate\) 시간이 필요하지만, 사용자 입장에서는 우선 화면이 보여지는 것이 중요합니다. 초기에 렌더링 되는 index.html이 비어있는 문서가 아니라 무언가 렌더링되어 있는 문서라면 [LCP\(Largest Contentful Paint\)](https://web.dev/i18n/ko/lcp/) 시점을 크게 앞당길 수 있을 것입니다.

## JAM Stack

서론이 길었는데요, 토스페이먼츠에서 만들고 있는 일부 제품에서 SSR\(Server Side Rendering\)없이 초기 렌더링 속도를 개선해 보았습니다. 어떤 결과를 낳았으며 어떻게 개선했는지 이야기하고자 합니다.

JAM Stack이란 JavaScript와 Markup에 해당하는 HTML, CSS 정적 리소스들을 활용하여 웹 애플리케이션을 구성하는 스택을 말합니다. 그리고 이 정적 리소스들을 CDN\(Content Delivery Network\)에 배포하여 서버 관리를 최소화 할 수 있습니다.

토스페이먼츠에서는 AWS S3, CloundFront, Lambda@edge 를 사용하여 인프라를 운영하고 있습니다.

→ [JAM Stack에 대해 더 알아보기](https://jbee.io/web/jam-stack/)

### SSG

Static Site Generation이라는 개념인데요, 앱을 빌드하는 시점에 미리 그려두고 이를 서빙\(serving\)하는 방식을 말합니다. JAM Stack에서 정적 리소스를 생성하는 용도로 사용합니다.

컴파일 단계에서 미리 그릴 수 있는 부분을 최대한 그려서 사용자에게 도달하는 최초 index.html 파일이 비어있지 않도록 합니다.

미리 그릴 수 있다는 것은 말 그대로 컴파일 단계에서 리액트 코드를 읽어 HTML로 렌더링 할 수 있는 부분을 말합니다. 정적인 부분을 포함하여 인증이 필요하지 않은 데이터 또한 서버로부터 가져와 미리 그릴 수 있습니다.

### 결과 \(지표\)

구체적인 내용을 다루기에 앞서 어느 정도의 개선이 있었는지 먼저 소개하고자 합니다. 기대한 것 이상의 결과가 나와서 매우 즐거웠던 경험이었습니다.

토스페이먼츠 상점관리자 초기 로딩 화면

### Lighthouse 지표

before

개선 하기 전 지표

After

개선 후 지표

### 구체적인 지표 측정

Chrome Browser에서 FP\(First Paint\)부터 LCP\(Largest Contentful Paint\)까지 걸린 시간을 측정해봤습니다.

before\(FP → LCP: 484ms\)

after\(FP → LCP: 0ms\)

> Large Contents에 해당하는 것을 일단 그려버리고 시작하니 0ms입니다.

최대한 그릴 수 있는 영역을 미리 그림으로써 사용자는 흰 화면을 마주하지 않고 바로 제품을 만나는 것과 같은 느낌을 받을 수 있습니다.

## How?

### [Next.js](https://github.com/vercel/next.js/)

토스페이먼츠의 프런트엔드 애플리케이션은 Next.js 라는 프레임워크를 사용하고 있습니다. Next.js는 서버 사이드 렌더링은 물론이고 앞서 설명드린 Static Site Generate 또한 지원합니다. \([Next.js Automiatic Static Optimization](https://nextjs.org/docs/advanced-features/automatic-static-optimization)\)

### [Suspense](https://ko.reactjs.org/docs/concurrent-mode-suspense.html)

우선 토스 대부분의 프런트엔드 애플리케이션 제품은 React의 Suspense를 통해 비동기를 제어하고 있으며 토스페이먼츠 제품 또한 예외가 아니었습니다. 이와 동시에 에러 핸들링 또한 [ErrorBoundary](https://ko.reactjs.org/docs/error-boundaries.html#gatsby-focus-wrapper)를 통해 제어하면서 비동기 상황을 제어하고 있습니다.

→ [\[SLASH 21\] 박서진 – 프론트엔드 웹 서비스에서 우아하게 비동기 처리하기](https://www.youtube.com/watch?v=FvRtoViujGg)

→ [선언적으로 에러 상황 제어하기](https://jbee.io/react/error-declarative-handling-3/)

이 Suspense를 Next.js와 함께 사용하기 위해선 약간의 추가 작업이 필요한데요, 앞서 설명드렸다시피 Next.js는 서버사이드 렌더링 또한 지원하는 프레임워크이기 때문에 Isomophic한 코드를 작성해야 합니다. 아쉽게도 Suspense는 서버사이드 렌더링이 지원되지 않습니다. \(글을 작성하는 시점에 [알파로 공개되어 있는 React 18](https://github.com/reactwg/react-18)에서 [개선](https://github.com/reactwg/react-18/discussions/22)될 예정\)

그래서 다음과 같이 Suspense를 한번 감싸서 사용해줄 수 있습니다.
    
    
    import { useState, useEffect, Suspense as ReactSuspense } from 'react';
    
    export function Suspense({ fallback, children }: ComponentProps<typeof ReactSuspense>) {
      const [mounted, setMounted] = useState(false);
    
      useEffect(() => {
        setMounted(true);
      }, []);
    
      if (mounted) {
        return <ReactSuspense fallback={fallback}>{children}</ReactSuspense>;
      }
      return <>{fallback}</>
    
    

이렇게 수정된 Suspense로 제어하고 있는 컴포넌트를 SSG로 빌드하게 되면 `fallback`이 렌더링됩니다.

다음과 같은 코드일 경우, SSG 시점엔 `<Loading />` 컴포넌트만 그려지게 됩니다.
    
    
    function UserPage() {
      return (
        <Suspense fallback={<Loading />}> // <- Render!
          <UserProfile />
          <UserDetailInfo />
        </Suspense>
    
    

즉, 빌드 단계에서 SSG로 미리 그려주고자 했던 UserPage에는 Loading 컴포넌트만 렌더링 될 뿐, `UserProfile` , `UserDetailInfo` 컴포넌트는 전혀 렌더링 되지 않습니다. 미리 렌더링하는 것에 대한 이점을 전혀 얻지 못하게 되는 것입니다.

번들 사이즈를 아무리 줄여도 사용자는 일단 로딩만 돌고 있는 흰 화면을 마주하게 되는 것입니다.

### 컴포넌트 배치 되돌아보기

우선 Suspense가 정말 필요한 컴포넌트인지, 레이아웃 영역인지 되돌아 볼 필요가 있습니다.

정말 Suspense가 필요한 영역이라면 `fallback` 컴포넌트를 정의해줄 때 로딩 컴포넌트만 정의해주지 않는다면 어떨까요? API 응답이 돌아오고 결국 그려질 컴포넌트와 응답이 오지 않았을 경우 보여줄 이 `fallback` 컴포넌트를 최대한 비슷하게 구성해주는 겁니다. 그렇다면 컴파일 시점에 그릴 수 있는 영역이 늘어나지 않을까요?

즉, 위와 같이 Loading 컴포넌트만 렌더링하지 않으려면 API 응답이 돌아왔을 때 그려져야 할 컴포넌트와 응답이 아직 돌아오지 않았을 때 보여줄 컴포넌트 두 벌이 최대한 비슷하게 구성되어 있어야 합니다.

### 컴포넌트와 API를 가깝게

처음 보셨던 화면에서는 총 16개의 API call이 존재합니다. 너무나 당연하게도 이 모든 API 응답은 제각각으로 올 것이고 모든 응답이 돌아오기를 기다렸다가 그려주는 것은 정말 낭비입니다.

  * 각각의 API들을 따로 격리시켜 서로의 렌더링을 block하지 않도록 합니다.
  * 데이터가 필요한 곳에서 가장 가까운 곳에서 API를 호출합니다. client caching이 이젠 너무나도 자연스럽기 때문에 이를 최대한 활용해줍니다.

`UserPage` 컴포넌트의 구조를 다음과 같이 변경해 볼 수 있습니다.
    
    
    function UserPage() {
      return (
        <Layout>
          <h1>사용자 정보</h1>
          <dl>
            <dt>이름</dt>
            <Suspense fallback={<dd>Loading</dd>}>
              <UserName />
            </Suspense>
          </dl>
          <h2>사용자 상세 정보</h2>
          <Suspense fallback={<div>Loading</div>}>
            <UserDetailInfo />
          </Suspense>
        </Layout>
      )
    }

페이지 컴포넌트\(`UserPage`\) 전체를 감싸고 있던 `Suspense` 컴포넌트가 사라지고 비동기로 처리되는 영역이 좁게 정의가 되었습니다. 또한 비동기 처리 과정 중 노출되는 컴포넌트의 모습도 원래 보여질 컴포넌트와 비슷하게 정의해줬습니다.

디자인이 필요한 영역이 늘었어요. API를 호출하고 기다리는 순간에 대해서도 디자인이 필요해요. 그대로 컴포넌트도 만들어줘야 하고 그만큼 손도 많이 갑니다. 하지만 서버 관리하는 비용보다 더 신경써줄 필요는 없다고 생각합니다.

조금만 신경쓰더라도 많은 개선을 볼 수 있는 방법입니다.

### 더 나아가기

지난 Next.js Conf에서 공식적으로 [React의 Server Component](https://ko.reactjs.org/blog/2020/12/21/data-fetching-with-react-server-components.html)를 사용한 렌더링 방식이 공개되었습니다. React 18도 알파 단계이니 프런트엔드 애플리케이션을 개발하면서 성능 상 이점을 많이 챙길 수 있는 환경으로 뒤바꿈 될 것 같습니다. [ISR 방식](https://nextjs.org/docs/basic-features/data-fetching/incremental-static-regeneration)과 컴포넌트 단위의 캐싱이 적용되어 웹이 더 빨라질 수 있을 것이라 기대합니다.

### 마무리

초기 로딩 속도가 중요한 것은 비즈니스에도 영향을 미치기 때문입니다. web.dev에서 초기 로딩 속도를 개선하여 성과가 개선된 사례가 소개된 바 있습니다.\(<https://web.dev/vitals-business-impact/>\)

당장에 SSR 도입이 쉽지 않은 상황이라면 SSG를 통한 초기 렌더링을 최적화 할 수 있습니다.

토스 팀은 계속해서 초기 로딩 속도를 계속해서 개선 중입니다. 곧 있을 SLASH22에서는 ‘매달, 유저가 기다리는 시간을 2.3년씩 아낄 수 있는 초기 렌더링 개선기 \(feat. SSR\)’라는 제목으로 초기 렌더링 개선 경험을 공유할 예정이니 많은 관심 부탁드립니다.

👉 [토스페이먼츠 프런트엔드 챕터에 대해 더 알아보기](https://tosspayments-dev.oopy.io/chapters/frontend/about)

감사합니다.