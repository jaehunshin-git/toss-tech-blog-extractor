# ESLint와 AST로 코드 퀄리티 높이기

**Date:** 2023년 3월 31일
**URL:** https://toss.tech/article/improving-code-quality-via-eslint-and-ast

---

## 코딩 컨벤션을 일관적으로 유지하기

일관적인 코딩 컨벤션을 가지면 코드를 읽기 쉬워지고, 안티패턴을 방지할 수 있습니다. 결과로 버그도 줄고, 코드를 쉽게 유지보수할 수 있죠.

하지만 이것을 사람이 직접 적용하는 것은 한계가 있기 때문에, 여러 가지 정적 분석 도구를 활용하게 됩니다. JavaScript/TypeScript 코드베이스에서는 주로 ESLint를 통해 컨벤션과 맞지 않는 코드를 사전에 감지하게 되는데요. 이러한 정적 분석 도구를 이용하게 되면 코드 리뷰 등 사람이 직접 읽지 않아도 컨벤션과 다른 부분을 기계적으로 잡아낼 수 있습니다.

## 이미 만들어진 규칙에서 오는 한계

ESLint에서는 생태계 내 다양한 플러그인 등을 통해 많은 수의 자주 사용되는 코딩 컨벤션을 커버할 수 있습니다. 하지만 우리 회사의 컨벤션에 맞는 규칙이 없다면 어떨까요? 조직이 커지고 요구 사항이 변화하게 되면서 커뮤니티에서 만들어진 규칙만으로는 조직 내 사용례에 정확히 부합하지 않는 경우가 생깁니다. 사내 라이브러리 내 사용 방식에 대한 컨벤션을 정의하거나, 조직 내 컨벤션과 커뮤니티에서 통용되는 컨벤션이 다소 다를 수도 있죠.

예를 들어 토스에서는 SSR을 통해 서버 사이드에서 React 렌더링을 한 뒤 애플리케이션에 제공해서 로딩 속도를 높이고 있는데요, 이로 인해 브라우저 환경에서 작동하는 코드가 서버 사이드에서 실행되면서 의도치 않은 버그를 유발하는 케이스가 있습니다. 이러한 경우 미리 브라우저에서 호환되지 않는 코드를 감지하여 사전에 오류를 예방할 수 있다면 큰 도움이 되겠죠.

### 린터는 어떻게 규칙을 적용할까?

이러한 제약 사항을 해결하기 위해서는 우리만의 ESLint 규칙을 정의할 수 있어야 합니다. 그런데 ESLint는 어떻게 코드에 대한 규칙을 만들고 적용하고 있을까요?

예를 들어서, Production 환경에서 로그가 함부로 찍히지 않도록 console.log 사용을 제한하는 규칙을 만드는 상황을 생각합시다.

간단하게 정규식으로 구현해보면 이런 형식이 될 것입니다.
    
    
    if (sourceCode.match(/console\\.log/) != null) {
      console.log("console.log를 사용하면 안 돼요!") 
    }

하지만 이 방법은 생각했던 만큼 잘 작동하지 않습니다.

예를 들어서, 이 코드에서 console.log가 문자열 안에 있는지도 알 수 없습니다.
    
    
    const message = "console.log()를 쓰지 마세요.";
    
    <Button>console.log 로그 활성화</Button>

주석 안에 있는지도 알 수 없죠.
    
    
    // console.log(…) 를 쓰지 마세요.

이러한 작은 케이스들을 하나하나 대응할 수도 있지만, ESLint는 좀 더 강력한 방법을 사용합니다.

### AST에서 원하는 정보 찾아내기

ESLint는 Abstract Syntax Tree\(AST\)를 이용해서 규칙을 정의하고 적용합니다.

AST는 소스 코드를 읽어낸 뒤 각 코드에서 구문 정보를 정리하여 나타낸 트리 형태의 자료 구조입니다. 예를 들어서, `console.log` 함수 호출과, 문자열이나 주석 속의 `console.log` 를 구별할 수 있게 해 줍니다.

AST의 상세한 구조는 파서마다 약간의 차이가 있지만, [AST Explorer](https://astexplorer.net/)라는 도구를 사용하면 소스 코드를 넣었을 때 어떤 AST가 나오는 지를 쉽게 확인할 수 있습니다. 일례로 `console.log()` 을 acorn이라고 하는 파서에서 파싱을 시도하면 이런 AST를 얻을 수 있습니다.
    
    
    {
      "type": "ExpressionStatement",
      "expression": {
        "type": "CallExpression",
        "callee": {
          "type": "MemberExpression",
          "object": { "type": "Identifier", "name": "console" },
          "property": { "type": "Identifier", "name": "log" }
        },
        "arguments": []
      }
    }

이와 다르게, 문자열에 포함되어 있는 console.log\(\) 의 파싱을 시도하면 이런 AST를 얻을 수 있습니다.
    
    
    { 
      "type": "Literal", 
      "value": "console.log()", 
      "raw": "\"console.log()\"" 
    }

함수를 호출하는 경우, CallExpression과 MemberExpression이 사용되고, 문자열 안에 있는 경우 Literal이 사용되는 것을 볼 수 있네요.

여기서 얻은 정보를 바탕으로 acorn을 이용해 console.log를 감지하는 스크립트를 작성해볼 수 있습니다.
    
    
    import { Parser } from "acorn";
    import { simple } from "acorn-walk";
    
    simple(Parser.parse(sourceCode), {
      CallExpression({ callee }) {
        if (callee.object.name === "console" && callee.property.name === "log") {
          console.log("console.log를 사용하면 안 돼요!");
        }
      },
    });

이렇게 `acorn-walk` 를 사용하면 CallExpression에 해당하는 console.log만 감지할 수 있습니다. 주석이나 문자열, 화이트스페이스에 관계없이 안전하게 소스코드를 분석할 수 있는 것이죠.

## ESLint에서 사용할 규칙 직접 정의하기

ESLint는 espree라고 하는 파서를 통해 소스 코드를 파싱하고, 이 결과를 각 플러그인에서 순회하며 규칙을 실행합니다. 우리가 원하는 규칙을 직접 플러그인을 통해 정의하고, 실행할 수 있어요.

Espree AST만 읽을 수 있다면 ESLint 규칙도 쉽게 만들 수 있습니다.

토스에서는 소스 코드 내에서 HTTP 링크를 찾아 HTTPS 링크로 바꿔야 한다고 알려주는 ban-http 와 같은 규칙을 정의하고 있습니다. 이런 규칙을 어떻게 직접 정의할 수 있는지 알아볼까요?

먼저 소스 코드 내 문자열이 Espree AST에서 어떻게 표현되는 지를 알아봐야 합니다. AST Explorer에서 상단의 파서 설정을 Espree로 변경해주면 이를 쉽게 알 수 있습니다.

Literal 타입의 노드에서 value를 읽으면 문자열 내용을 알 수 있네요.
    
    
    {
      "type": "Literal",
      "value": "http://toss.im",
      "raw": "\"http://toss.im\""
    }

이를 기반으로 아래와 같이 ESLint 규칙을 새로 정의할 수 있습니다.
    
    
    module.exports = {
      meta: {
        /* ... */
      },
      create: function (context) {
        return {
          Literal: function (node) {
            if (typeof node.value !== "string") {
              return;
            }
            if (node.value.indexOf("http://") >= 0) {
              context.report({ node, messageId: "isHttpBanned" });
            }
          },
        };
      },
    };

위 코드는 Literal을 만났을 때, 그 Literal의 값이 “http://” 로 시작하는 문자열이면 에러를 리포트하는 코드입니다. 생각보다 복잡하지는 않죠?

이렇게 작성된 규칙을 ESLint에 추가하면 개발자들이 개발 중 규칙에 맞지 않는 코드를 작성했을 때 이렇게 알려줄 수 있어요.

## 토스에서 사용하는 여러가지 규칙들

이를 바탕으로 토스에서는 여러 가지 ESLint 규칙을 만들어서 플러그인으로 배포하고, 이를 서비스에서 사용하여 코딩 컨벤션을 유지하고 있습니다. 몇 가지 사용하는 규칙들은 아래와 같은 규칙들이 있어요.

  * 토스 프론트엔드 챕터 내 맥락이 강한 규칙들

    * 사내 라이브러리 사용 시 deprecated된 API 사용 금지
    * 이전 토스 도메인 사용 금지

  * 외부 라이브러리 사용에 관련한 규칙들

    * 사용하지 않기로 한 패키지 사용 제한 \(ban-axios, ban-lodash\)
    * 훅 이름에서 한글 허용 \(rules-of-hooks\)
    * SSR에서 사용 시 오류를 내는 라이브러리 사용 제한 \(ban-ssr-unsafe-method\)

또한 ESLint 외에도 자체 제작한 도구를 통해 사용해 deperecated 된 API의 사용이나 중복된 코드를 감지하기도 해요.

## 더 알아보기

ESLint 플러그인을 만드는 방법과 ESLint API 자체에 대한 글은 ESLint 공식 문서에서 더 자세히 알 수 있어요.

[Create Plugins – ESLint – Pluggable JavaScript Linter](https://eslint.org/docs/latest/extend/plugins)