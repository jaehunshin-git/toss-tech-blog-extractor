# JSCodeShift로 기술 부채 청산하기

**Date:** 2021년 5월 4일
**URL:** https://toss.tech/article/jscodeshift

---

토스 프론트엔드 챕터에서는 100개 이상의 서비스들이 작은 패키지 단위로 쪼개져 활발하게 개발되고 있는데요. 공통으로 사용하는 라이브러리에서 인터페이스가 변경되는 Breaking Change가 발생하면, 의존하고 있는 모든 서비스의 코드를 수정해야 했습니다. 관리하는 코드베이스가 점점 커지면서 해야 하는 작업의 양도 계속 늘어나고는 했습니다.

이에 프론트엔드 챕터는 JSCodeShift를 도입하여 대부분의 코드 수정 작업을 자동화할 수 있었습니다. 토스팀이 JSCodeShift를 도입하면서 알게 된 점과 노하우를 테크 블로그로 공유합니다.

## JSCodeShift란?

[JSCodeShift](https://github.com/facebook/jscodeshift)는 Facebook이 만든 JavaScript/TypeScript 코드 수정 도구입니다. JSCodeShift를 통해 코드를 수정하는 코드를 작성할 수 있습니다.

## 찾아 바꾸기와의 비교

JSCodeShift를 도입하기 전, 토스에서는 대량의 코드 수정이 필요할 때면 IDE의 찾아 바꾸기\(Find & Replace\)를 사용했습니다. 그러나 찾아 바꾸기로는 안전하게 코드를 수정하는 데에 한계가 많았습니다.

### 예시 1: console.log\(\) 모두 삭제하기

프로젝트 전체에 있는 `console.log()` 호출을 모두 제거하고 싶은 상황을 생각해봅시다. 간단한 예제임에도 쉽게 고칠 수 없는 엣지 케이스들이 발생합니다. 우선 console.log 안에 들어가는 인자의 내용이 달라질 수 있습니다. console.log에 여러 인자를 넘겨서 함수 호출이 여러 줄에 걸칠 수도 있습니다.

이것을 정규식을 이용하여 어느 정도 해결할 수도 있습니다. 그러나 다양한 엣지케이스에 대응하기 위해서 정규식이 점점 복잡해지는 경우가 발생했습니다. 또 정규식은 정규 언어이기 때문에 기술적으로 대응할 수 없는 경우도 존재했습니다.

### 예시 2: default import된 객체의 프로퍼티 수정하기

아래와 같은 코드가 있었다고 생각해봅시다.
    
    
    import A from '@tossteam/a';
    
    A.foo();

어느 순간 `A.foo()` 함수가 `A.bar()` 함수로 이름이 변경되었다고 가정해봅시다.

Default import의 변수 이름은 사용하는 사람마다 임의로 정할 수 있기 때문에, 어떤 사람은 이 라이브러리를 `B` 라고 하는 이름으로 사용하고 있을 수도 있습니다. 때문에 이 라이브러리를 `B.foo()` 처럼 사용하고 있던 코드가 있었다면, `B.bar()` 로 수정해주어야 합니다.

이런 경우는 찾아 바꾸기로 쉽게 대응하기 어렵습니다.

## JSCodeShift 기초

JSCodeShift는 추상 구문 트리\(AST, Abstract Syntax Tree\)를 이용하여 코드를 수정하는 방법을 제공함으로써 코드 수정 작업을 정확하고 편리하게 할 수 있도록 도와줍니다.

### 추상 구문 트리 \(AST\)

추상 구문 트리는 프로그램의 소스 코드를 쉽게 다룰 수 있도록 도와주는 자료구조입니다.

예를 들어서, 다음 `import` 문을 추상 구문 트리로 옮기면 이런 모습이 됩니다.
    
    
    import React, { useMemo } from 'react';
    
    
    ImportDeclaration {
      specifiers: [
        ImportDefaultSpecifier {
          local: Identifier {
            name: "React"
          }
        },
        ImportSpecifier {
          local: Identifier {
            name: "useMemo"
          }
        }
      ],
      source: Literal {
        value: "react"
      }
    }

살펴보면 `import` 문이 `ImportDeclaration` 객체로 바뀌었습니다. 또 내부에서 사용되는 Default Import와 Named Import, 라이브러리 이름이 알맞은 객체로 옮겨진 것을 확인할 수 있습니다.

### ASTExplorer

작성한 코드의 추상 구문 트리를 [ASTExplorer](https://astexplorer.net/)로 쉽게 확인할 수 있습니다. 코드만 붙여넣으면 해당하는 구문 트리를 바로 확인할 수 있어 편리합니다. 소스 코드의 특정 부분에 커서를 옮기면 그 부분이 트리의 어떤 부분에 해당하는지 바로 볼 수 있기도 합니다. 😉 추상 구문 트리에 익숙하지 않다면, 사용해보시는 것을 권장합니다.

### 라이브러리별 추상 구문 트리

라이브러리마다 사용하는 추상 구문 트리의 모습은 다를 수 있습니다. 예를 들어서 같은 JavaScript를 다루더라도 ESLint가 사용하는 트리와 Babel이 사용하는 트리는 약간 다릅니다. JSCodeShift는 Babel이 사용하는 트리를 사용하고 있습니다.

ASTExplorer 상단 메뉴에서 사용할 추상 구문 트리를 선택할 수 있습니다. JSCodeShift가 사용하는 트리는 `@babel/parser` 입니다.

## JSCodeShift 사용하기

JSCodeShift로 코드를 수정하는 과정은 크게 4가지 작업으로 나눌 수 있습니다.

  1. AST로 파싱: 파일의 소스 코드를 AST로 파싱합니다.
  2. 수정할 노드 선택: AST에서 수정할 노드를 선택합니다.
  3. 수정하기: 검색한 노드를 JSCodeShift가 제공하는 유틸리티로 코드를 변경시킵니다.
  4. 소스 코드로 내보내기: 수정된 AST를 JavaScript 소스 코드로 내보냅니다.

예를 들어, 이런 형식으로 코드를 작성합니다.
    
    
    /* transformSomeCode.js */
    function transformSomeCode(file, { jscodeshift }) {
      // 1. AST로 파싱
      const tree = jscodeshift(file.source);
    
      // 2. 수정할 노드 선택
      const nodes = tree.find(...);
    
      // 3. 수정
      jscodeshift(nodes)
        .remove() | .replaceWith() | .insertBefore()
    
      // 4. 소스 코드로 내보내기
      return tree.toSource();
    }

이후 JSCodeShift CLI를 이용하여 `jscodeshift -t transformSomeCode.js <target>` 와 같은 명령을 실행하면 `<target>` 에 있는 소스 코드들이 `transformSomeCode.js` 에 정의된 규칙에 맞게 수정됩니다.

이제 본격적으로 JSCodeShift에서 자주 사용되는 메서드들을 살펴보겠습니다.

### 수정할 노드 선택하기: find\(\)

기본적으로 수정할 노드를 선택하기 위해 `find()` 함수를 사용합니다.

예를 들어, `react` 라이브러리의 `useMemo` 를 가져오는 `import` 구문들을 선택하기 위해서는 아래와 같이 코드를 작성할 수 있습니다.
    
    
    const nodes = tree.find(
      /* 찾을 AST 노드 타입 */
      jscodeshift.ImportDeclaration,
      /* 필터링할 함수 */
      node => {
        return (
          /* ImportDeclaration 중에서 */
          node.type === 'ImportDeclaration' &&
          /* react 라이브러리에서 */
          node.source.value === 'react' &&
          /* 가져오는 것 중에서 */
          node.specifiers.some(specifier => {
            /* useMemo를 포함하는 것을 */
            return (
              specifier.type === 'ImportSpecifier' &&
              specifier.imported.name === 'useMemo'
            );
          })
          /* 선택한다 */
        )
      }
    );

### 노드 삭제하기: remove\(\)

선택한 노드를 삭제하기 위해 `remove()` 함수를 사용합니다.

예를 들어서, 아래와 같이 코드를 작성함으로써 선택한 `node` 의 목록을 삭제할 수 있습니다.
    
    
    for (const node of nodes) {
      jscodeshift(node).remove();
    }

### 노드를 다른 노드로 치환하기: replaceWith\(\)

선택한 노드를 새로운 노드로 치환하려고 할 때 `replaceWith()` 함수를 사용할 수 있습니다.

예를 들어서, 선택한 `node` 들을 다른 모습으로 치환하기 위해서는 아래와 같이 코드를 작성할 수 있습니다.
    
    
    for (const node of nodes) {
      /* 노드를 만드는 방법에 대해서 아래에서 더 자세히 다룹니다. */
      const newNode = createNode();
    
      jscodeshift(node).replaceWith(newNode);
    }

### 새로운 노드 만들기

`replaceWith()` 와 같은 함수에서 사용하기 위해서 새로운 노드를 만들 때는 JSCodeShift에서 제공하는 도우미 함수들을 사용할 수 있습니다.

> 각 노드를 만드는 방법을 모두 알 필요는 없습니다. TypeScript를 사용하는 경우, 각 함수가 어떤 인자를 받는지 바로 확인할 수 있습니다. JavaScript를 사용하는 경우, ast-types가 정의하는 타입 정보를 참고해주세요.

변수 참조:`foo`와 같은 변수에 참조하는 노드를 만들기 위해서 `jscodeshift.identifier()` 를 사용할 수 있습니다.
    
    
    jscodeshift.identifier('foo');

멤버 접근: 변수 `foo`의 멤버 `bar` 에 접근하는 노드를 만들기 위해서 `jscodeshift.memberExpression()` 을 사용할 수 있습니다.
    
    
    jscodeshift.memberExpression(
      jscodeshift.identifier('foo'),
      jscodeshift.identifier('bar')
    );

import 문:`import { useMemo } from 'react';` 와 같은 `import` 문을 만들기 위해서 `jscodeshift.importDeclaration()` 을 사용할 수 있습니다.
    
    
    jscodeShift.importDeclaration(
      [
        jscodeShift.importSpecifier(
          jscodeshift.identifier('useMemo')
        )
      ],
      jscodeshift.literal('react')
    );

## JSCodeShift 사용 예시

토스 프론트엔드 챕터에서는 2020년 `import { Adaptive } from '@tossteam/web-development-kits'` 와 같은 `import` 문을 모두 `import { adaptive } from '@tossteam/colors'` 으로 수정해야 하는 필요성이 있었습니다.

이런 경우는 찾아 바꾸기로 해결하는 데에 어려움이 있었습니다. 코드를 수정하는 규칙이 복잡했기 때문입니다.

  1. `@tossteam/web-development-kits` 라이브러리로부터 `Adaptive` 뿐 아니라 다른 변수나 함수를 import 하는 경우가 있었습니다. 그런 경우에는 전체 import 문을 지우는 것이 아닌, `Adaptive` 를 가져오는 부분만 삭제해야 했습니다.
  2. `Adaptive` 를 import하는 부분이 삭제된 경우에만 `import { adaptive } from '@tossteam/colors';` 와 같이 새로운 import 문을 파일의 가장 처음에 추가해주어야 했습니다. 아닌 경우, 사용하지 않은 변수로 인해 컴파일 시간에 오류가 발생했습니다.
  3. `Adaptive` 를 import하는 부분이 삭제된 경우에만 그 파일에서 사용되는 모든 `Adaptive` 변수를 `adaptive` 로 바꿔줘야 했습니다.

다행히 토스팀에서는 간단히 이 문제를 JSCodeShift로 해결할 수 있었습니다. 저희가 설계한 JSCodeShift 변환 코드의 구조는 다음과 같습니다.
    
    
    function transformLegacyImportToNewImport(file, { jscodeshift }) {
      const root = jscodeshift(file.source);
    
      /* 오래된 import 문들을 찾음 */
      const oldImports = findOldImports(root, { jscodeshift });
    
      /* 오래된 import 문이 없는 파일인 경우, 아무 작업을 하지 않음 */
      if (oldImports.length === 0) {
        return;
      }
    
      for (const oldImport of oldImports) {
        /* 오래된 import 문에서 Adaptive를 가져오는 부분을 삭제 */
        /* (Adaptive만을 가져오는 import 문인 경우, import 문 전체를 삭제) */
        removeImportMember(root, oldImport, 'Adaptive', { jscodeshift });
      }
    
      /* @tossteam/colors에서 adaptive를 import하는 부분을 추가 */
      /* (@tossteam/colors를 import하고 있지 않은 경우, import 문을 추가) */
      addImportMember(root, '@tossteam/colors', 'adaptive', { jscodeshift });
    
      /* Adaptive 변수를 모두 adaptive로 치환 */
      const oldAdaptives = findIdentifiers(root, 'Adaptive', { jscodeshift });
    
      for (const oldAdaptive of oldAdaptives) {
        jscodeshift(oldAdaptive).replaceWith(
          jscodeshift.identifier('adaptive')
        );
      }
    
      /* 수정된 소스코드를 반환 */
      return root.toSource();
    }
    
    

이 중에서 `removeImportMember` 함수와 같은 경우, 아래와 같이 간단히 구현할 수 있었습니다.
    
    
    function removeImportMember(root, importNode, name, { jscodeshift }) {
      const oldSpecifiers = importNode.value.specifiers;
    
      /* name을 import하는 부분을 삭제 */
      const newSpecifiers = oldSpecifiers.filter(specifier => {
        return (
          specifier.type !== 'ImportSpecifier' ||
          specifier.imported.name !== name
        );
      }
    
      /* 더 이상 import할 것이 남지 않은 경우에는, import 문을 삭제 */
      if (newSpecifiers.length === 0) {
        jscodeshift(importNode).remove();
        return;
      }
    
      /* 그렇지 않은 경우, import 문에서 name을 가져오는 부분만 삭제 */
      jscodeshift(importNode).replaceWith(
        jscodeshift.importDeclaration(
          newSpecifiers,
          importNode.value.source
        )
      );
    }

다른 함수의 경우에도 유사하게 JSCodeShift API를 이용하여 구현할 수 있었습니다.

## JSCodeShift 테스트하기

JSCodeShift는 작성한 변환 코드가 잘 작동하는지 테스트할 수 있도록 `testUtils` 라고 하는 이름의 테스트 도구를 제공합니다. 테스트 파일의 디렉토리 구조를 JSCodeShift가 요구하는 대로 맞춰야 하지만, 손쉽게 Jest에 테스트를 붙일 수 있어서 편리합니다.

테스트가 잘 붙어 있으면, JSCodeShift 코드의 문제점을 바로바로 찾을 수 있게 됩니다. 개발 속도도 절약되는 만큼, JSCodeShift를 개발할 때는 꼭 테스트와 함께 하는 것을 추천합니다.

JSCodeShift 테스트와 관련된 자세한 내용은 [JSCodeShift README](https://github.com/facebook/jscodeshift#unit-testing)에서 확인할 수 있습니다.

## 토스팀과 JSCodeShift

토스 프론트엔드 개발팀은 짧은 시간동안 빠르게 개발환경을 개선해오면서 대량의 레거시 코드를 최신 라이브러리와 코드 컨벤션에 맞추도록 수정해주어야 했습니다. 경우에 따라서는 작성된지 2년이 지난 오래된 코드가 수만 줄 이상 존재하기도 했습니다.

이때 JSCodeShift를 사용함으로써 그런 코드도 한번에 최신 코드와 같이 일관성을 맞출 수 있었습니다. 이번 JSCodeShift 가이드가 레거시 시스템을 다루는 다른 프론트엔드 개발자 분들께 도움이 되었으면 합니다.