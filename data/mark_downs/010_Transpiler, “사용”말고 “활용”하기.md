# Transpiler, “사용”말고 “활용”하기

**Date:** 2024년 5월 24일
**URL:** https://toss.tech/article/27750

---

안녕하세요. 토스뱅크 프론트엔드 개발자 강현구입니다.

프론트엔드 개발자라면 transpiler를 한 번쯤은 들어보거나 사용해 봤을 거예요. 프론트엔드 생태계가 빠르게 발전하면서, transpiler는 애플리케이션을 만들고 배포하는 과정에서 빠질 수 없는 필수 요소가 되었어요.

토스뱅크에서는 개발 경험을 향상하기 위해서 transpiler를 다양하게 활용하고 있는데요. 오늘은 transpiler로 로깅 과정을 개선한 사례를 소개 드릴게요.

## Transpiler란?

Transpiler는 코드를 변환하는 도구를 의미해요. JavaScript의 ES6 문법을 ES5 문법으로 변환하거나, React의 JSX 및 Typescript 코드를 브라우저가 이해할 수 있는 Javascript로 변환하는 도구에요. Transpiler 덕에 여러 브라우저 호환성을 유지하면서 다양한 문법을 활용할 수 있죠.

대표적인 transpiler로는 Babel과 SWC가 있어요. 토스뱅크는 마이크로 프론트엔드 구조로 여러 서비스들의 각자 입맛에 맞게 Babel과 SWC를 사용하고 있어요. 

언급한 내용만으로도 transpiler가 개발자에게 가져다준 편의성은 굉장해요. 비즈니스 로직에만 집중할 수 있도록 코드를 작성하는데 편리함을 제공하고, 부가적인 작업은 알아서 처리해 주는 거죠. 매일 이렇게 “사용”만 하는 transpiler, 토스뱅크에서는 한 단계 더 잘 “활용”해 보기로 했어요.

## 로깅이란?

토스뱅크는 데이터 기반으로 의사결정이 이루어져요. 올바른 결정을 위해서 개인정보 등 민감 정보를 제외한 유저의 클릭, 페이지뷰 등 다양한 유저 활동에 대한 데이터를 수집하고 있어요. 이 과정을 `로깅`이라고 해요. \(유저의 데이터는 개인정보 처리 동의를 기반으로 수집하고 이용해요\)

로깅은 대부분의 서비스 코드에서 필요해요. 그래서 적절히 추상화하여 비즈니스 로직과 구분할 필요가 있어요. 전반적인 개발 경험을 해치지 않으면서 유저 데이터를 쌓기 위해서죠.

또한 효율적으로 데이터를 수집하려면 화면에서 발생하는 모든 클릭 이벤트를 로깅하지 않고, 유의미한 정보만 로깅해야 해요. 예를 들어, 실제로 clickable한 버튼을 클릭했을 경우엔 로깅하고, clickable하지 않은 글자나 빈 화면을 클릭한 경우는 무시해야겠죠. 

여러분은 로깅을 어떻게 설계할 것 같나요? 크게는 아래 두 가지 방식이 있어요.

  * 수동으로 로깅 함수를 실행하는 방식
        
        <Button
          onClick={() => {
            log({ content: '다음' });
            handleClick();
          }}
        >
          다음
        </Button>

  * 추상화된 로깅 컴포넌트를 활용하는 방식
        
        <LoggingClick>
          <Button onClick={handleClick}>
            다음
          </Button>
        </LoggingClick>

이외에도 여러 다양하고 창의적인 방식들이 많을 것 같아요. 하지만 아무것도 하지 않아도 로깅이 알아서 되면 어떨까요? 토스뱅크에서는 원래 로깅을 어떻게 하고 있었고, transpiler로 로깅을 자동화한 방법을 알려드릴게요.

## 2% 부족한 클릭 로깅

기존에 토스뱅크 프론트엔드 챕터가 선택한 클릭 로깅 방식은 다음과 같아요. 이벤트 캡처링\(window listen\)과 data attribute 두 가지를 활용해서 로깅을 처리했어요. 
    
    
    <Button onClick={() => {}} data-click-log>
      다음
    </Button>

유저가 버튼을 클릭했을 때, click event를 캡처링을 통해 인지하고, 클릭 타깃에서 가장 가까운 `data-click-log` 속성을 지닌 DOM을 찾아요. 찾은 DOM의 text node를 파악하여 유저가 클릭한 컴포넌트의 정보를 아래와 같이 로깅해요.
    
    
    {
      log_type: 'click',
      content: '다음',
    }

하지만 매번 `data-click-log`를 붙이는 일이 번거로웠어요. 타이핑에 실수가 생기면 로그가 누락될 수 있는 위험도 존재했어요. Props가 많아진다면 문제를 찾기 더 어려웠죠.
    
    
    <Button
      type="primary"
      variant="weak"
      size="large"
      data-cilck-log // 오타
      onClick={() => {}}
      disabled={false}
      loading={false}
      css={{ minWidth: 100, minHeight: 80 }}
    >
      다음
    </Button>

단순 실수를 줄이기 위해 별도의 lint rule을 추가하거나, 자동완성 기능을 제공하는 방향도 고려했지만, 문제가 발생하는 근본적인 원인을 해결하기로 했어요.

## 부족한 2% 채우기

토스뱅크의 기존 로깅 방식을 다시 정리해 볼게요. 

> 클릭 이벤트가 발생하면, `data-click-log` 속성을 지닌 DOM을 찾아 로깅한다

이벤트 발생 시 로깅해주는 시스템은 이미 충분히 자동화가 되어있었어요. 그래서 clickable한 요소에 `data-click-log` 속성을 자동으로 주입해 줄 수만 있다면, 문제를 근본적으로 해결하여 부족한 2%를 채울 수 있다고 판단했어요. 

아래 1번 코드가 2번 코드로 변환되면 문제를 해결할 수 있었죠. 
    
    
    1. 
    <Button onClick={() => {}}>
      다음
    </Button>
    
    2.
    <Button onClick={() => {}} data-click-log>
      다음
    </Button>

“특정한 조건에 따라, 알맞게 코드를 변환하는 것” transpiler가 적합한 도구라고 판단했어요. Clickable한 요소라는 조건에 따라, `data-click-log` 속성이 들어가도록 코드를 변환하는 거죠.

## Transpiler로 로깅 플러그인 만들기

Clickable 하다는 것은 `onClick`, `onChange`, `onTouchStart`와 같은 유저의 클릭에 반응하는 이벤트 핸들러가 존재하는 것이라고 규정한다면, clickable 조건에 대한 판단도 충분히 할 수 있었어요. 

이런 특징을 활용해서 SWC와 Babel용 플러그인을 만들었어요. 

Babel용 플러그인을 예시로 소개해볼게요. 
    
    
    const CLICK_EVENTS = ['onClick', 'onTouchStart', 'onChange', 'onMouseDown'];
    const CLICK_LOG_ATTR = 'data-click-log';
    
    function plugin({ types: t }: typeof babel): PluginObj {
      return {
        name: 'babel-plugin-tossbank-logger',
        visitor: {
          JSXOpeningElement(path) {
            const { node } = path;
    
            const hasOnClickAttribute = node.attributes.some(attr => {
              return CLICK_EVENTS.includes(attr.name.name);
            });
    
            if (hasOnClickAttribute) {
              const dataClickLogAttribute = t.jSXAttribute(t.jSXIdentifier(CLICK_LOG_ATTR), null);
    
              node.attributes.push(dataClickLogAttribute);
            }
          },
        },
      };
    }

Babel은 AST\(추상구문트리\)를 만들고, 이를 플러그인에게 제공하여 각 노드들을 순회하며 처리할 수 있도록 인터페이스를 제공하고 있어요. Visitor의 JSXOpeningElement는 JSX 태그의 시작 요소들을 순회하며 실행할 콜백을 정의한 거예요. 

위 코드를 살펴보면 각 요소들을 순회하며 해당 노드가 `onClick` ,`onTouchStart`, `onChange`, `onMouseDown`처럼 clickable 한 이벤트 핸들러가 존재하는지\(`hasOnClickAttribute`\) 체크해요. clickable 한 이벤트가 존재한다면 `data-click-log` 라는 data attribute를 주입하고 있어요. 

SWC용 플러그인도 마찬가지로 동일한 로직에 Rust 기반으로 만들어 제공했어요. 

이 로깅 플러그인을 활용하는 개발자는 아래 코드와 같이 클릭 로깅을 생략하고 비지니스 로직만 작성할 수 있게 된거예요.
    
    
    <Button onClick={() => {}}>
      다음
    </Button>

이 외에도, 클릭한 요소가 어떤 디자인 시스템 컴포넌트인지 자동으로 로깅 처리를 할 수도 있고, 특정 조건에서는 클릭 로깅을 방지하는 등 원한다면 활용할 수 있는 범위는 더 넓어요. 

이제 누가 개발을 하던 항상 동일하게 로깅을 처리하고, 동일한 로깅 결과가 나오도록 보장할 수 있게 되었어요. 

## 새로운 시선으로 바라보기

로깅 외에도 토스뱅크에서는 다국어 처리에 transpiler를 활용하고 있어요. Transpiler는 아직 생각하지 못한 더 다양한 영역에서 우리의 개발 경험을 개선해 줄 거라고 생각해요. 

여러분도 이런 코드가 있다면 transplier를 활용할 수 있을지 고민해 보면 어떨까요? 

  * 반복적, 규칙적으로 코드 변경\(작성/수정/삭제\)이 필요하고
  * 누락과 오타 등 휴먼 에러가 빈번하게 발생하며
  * 비즈니스 로직을 침범하는 코드들

Transpiler를 예시로 이야기했지만, 다른 도구들도 마찬가지로 “어디에 쓰이는지”보단 “무엇을 하는지”를 알면, 마주한 문제들을 예상보다 쉽고 창의적이게 해결할 수 있어요. 토스뱅크 프론트엔드 챕터는 앞으로도 사용하는 도구들을 다양한 방면으로 활용해서, 마주한 문제들을 쉽게 해결할 수 있도록 고민해 나아갈 거예요.