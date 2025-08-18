# Node.js 라이브러리 배포 파이프라인에 플러그인 시스템 도입기

**Date:** 2024년 8월 14일
**URL:** https://toss.tech/article/nodejs_pipeline_plugin

---

토스 노드 챕터는 다수의 라이브러리를 관리하고 있어요. 라이브러리 관리에 이토록 진지하게 접근하는 팀을 찾기는 쉽지 않죠.

2021년 4월, 저희 팀은 첫 모노레포를 만들었어요. 이제는 그 모노레포에만 100개가 넘는 라이브러리가 존재하죠. 현재는 이런 라이브러리 모노레포를 코어만 6개를 운영 하고있어요. 서버 라이브러리, 코어 전용 라이브러리, CA라이브러리 등 성격에 맞게 모아두었어요.

패키지 수가 늘어남에 따라, 라이브러리 모노레포가 더 생겨남에 따라 여러 시행착오가 있었어요.

오늘은 저희가 어떻게 많은 라이브러리를 관리하는지, 어떤 시행착오를 겪었는지, 그리고 그 과정에서 축적된 노하우와 경험들을 공유하고자 합니다. 저희의 이야기가 여러분의 라이브러리 관리 방식을 한 단계 업그레이드하는 데 도움이 되었으면 합니다.

## 복잡해지는 deploy-cli

코어 및 계열사가 운영하는 다양한 라이브러리 레포, 모노레포 배포 파이프라인에서 공통적인 부분은 유지하면서 다양한 요구사항을 만족하기 위해 deploy cli에 옵션이 늘어나기 시작했어요
    
    
    $ deploy-cli --codegen-export --validate-build-output --collect-usage

요구사항이 생기고 이를 반영하기 위해 코드가 늘어남에 따라 deploy cli가 복잡해졌어요. 매번 옵션추가/수정 후 deploy cli 업데이트 & option on을 해줘야 했고 개별 레포/계열사의 요구사항을 만족하려면 공통 라이브러리를 작업해야 하는 문제가 있었어요.

## Plugin 시스템 도입하기

기존의 불편함을 해결하기 위해 새로운 시스템은 다음 요구사항을 만족할 수 있어야 합니다

  1. 독립성: 공통 배포 라이브러리 수정/업데이트 없이 작업과 적용이 가능해야 함
  2. 다양성: 레포별/계열사별 여러 가지 요구사항을 만족할 수 있어야 함
  3. 개발자 경험: 원하는 시점에 원하는 정보를 쉽게 이용하여 구현할 수 있어야 함

이를 해결하기 위해 plugin 시스템을 고안했어요. deploy plugin은 공통 배포 라이브러리 수정 없이 요구사항을 독립적으로 구현하고 배포할 수 있는 시스템이에요. 플러그인 시스템을 이용하면 계열사/레포별로 다양해진 요구사항을 유연하게 적용할 수 있어요.

새 시스템을 구성하면서 ESlint와 같이 Node.js 생태계에서 plugin 시스템을 구현한 곳들을 참고하였습니다. Plugin 시스템이 위 요구사항들을 잘 만족한다고 판단했습니다.

#### 잠깐, 플러그인이란? \(from GPT\) 플러그인은 "plug in"이라는 영어 표현에서 유래되었습니다. 이는 시스템에 새로운 기능이나 확장을 "꽂아 넣는다"라는 의미를 담고 있습니다. 플러그인은 기존 시스템에 별도의 코드 수정 없이 새로운 기능을 추가할 수 있는 모듈을 의미합니다. 전자 기기에서 플러그를 꽂아 기능을 확장하는 것처럼, 소프트웨어에서도 플러그인을 통해 기능을 확장할 수 있기 때문에 이러한 이름이 붙여졌습니다.

### eslint plugin

모두 ESlint 설정을 해보셨을 텐데요. ESlint도 plugin 시스템을 구성하여 활발히 이용하고 있습니다. 아래와 같이 plugin 라이브러리를 설치한 후 config에 적용하기만 하면 기능이 바로 활성화됩니다.
    
    
    // eslint.config.js
    import example from "eslint-plugin-example";
    
    export default [
      {
        plugins: {
          example,
        },
        rules: {
          "example/rule1": "warn",
        }
      }
    ];

ESlint는 플러그인이 존재하고 원하는 플러그인을 옵션도 넣어서 이용할 수 있습니다. ESlint와 같은 플러그인 방식이 우리의 요구사항을 잘 만족한다고 생각했고 이를 참고하여 deploy plugin을 구상하였습니다.

### 구성

먼저 plugin spec을 정의합니다. spec에 맞게 구현하고 배포된 라이브러리는 deploy plugin으로 이용될 수 있습니다.
    
    
    type PluginIndex = {
      npm: {
        hook: NpmDeployHook;
      }
    };

hook을 구현하여 export 한다면 원하는 시점에 원하는 정보를 이용하여 배포 사이클 사이사이에서 코드를 실행할 수 있습니다.
    
    
    type NpmDeployEvent = {
      alpha: boolean;
      monorepo: boolean;
      mainBranch: string;
    } & (
      | { type: 'before all' }
      //
      | { type: 'before version up all'; packages: Package[] }
      | { type: 'before version up each'; pkg: Package }
      | { type: 'after version up each'; pkg: Package }
      | { type: 'after version up all'; packages: Package[] }
      //
      | { type: 'before publish all'; packages: Package[] }
      | { type: 'before publish each'; pkg: Package }
      | { type: 'after publish each'; pkg: Package }
      | { type: 'after publish all'; packages: Package[] }
      //
      | { type: 'after all'; packages: Package[] }
    );

예를 들어 배포 전 빌드 결과를 스캔하는 플러그인을 만든다면 다음과 같이 구현이 가능합니다.

  1. 먼저 적절한 이벤트를 받아 핸들링하는 코드를 작성합니다.
         
         // src/index.ts
         
         hook.on('before publish each', ({ pkg }) => {
           await scan(pkg);
         });
         
         export const npm = {
           hook,
         };

  2. deploy-plugin spec에 맞춰 배포합니다.
         
         @toss/deploy-plugin-scan

  3. 적용을 원하는 레포에 설치합니다
         
         pnpm add -D @toss/deploy-plugin-scan

  4. plugin 설정이 있다면 추가합니다.
         
         module.exports = {
           plugins: {
             "@toss/deploy-plugin-scan": {
               "ignores": ["foo*"],
             }
           }
         };

## 토스는 Plugin 이렇게 사용해요

토스 커뮤니티에서 유용하고 사용하고 있는 plugin 몇 가지를 소개해드릴게요. 

### 1\. deploy-plugin-codegen

노드 챕터에서는 자체 개발한 CodeGen을 여러 가지 용도로 사용합니다. 대표적으로 index export 기능이 있는데 명시적으로 export가 가능하도록 주석으로 마킹한 컴포넌트만 export 하도록 해주는 CodeGen입니다.

이러한 CodeGen들이 적절히 실행되었는지 CI/CD에서 확인할 수 있도록 CodeGen plugin이 필요합니다.

### 2\. deploy-plugin-collect-usage

라이브러리와 제공하는 기능이 많아질수록 라이브러리가 어디서 얼마나, 어떻게 쓰이는지 알기 힘들어졌습니다. 기능이 변경될 때 어느 제품이 영향받을지 알 수 있도록, 어떤 기능을 수정/삭제할 때 영향도를 알 수 있도록 어떤 라이브러리 어느 버전, 어떤 기능을 어느 서비스에서 쓰는지 collect하도록 하였습니다.

서비스에서 collect도 실행하고 라이브러리 모노레포에서는 `deploy-plugin-collect-usage` 를 만들어 Public API 사용 현황을 수집하여 관리에 참고하고 있습니다.

### 3\. deploy-plugin-lightweight

`package metadata`는 package의 모든 메타정보를 내려주고 있습니다. 버전이 많아질수록 커지는 구조인 것이죠. 배포 빈도가 많은 라이브러리는 metadata가 매우 커져 MB 단위가 되고 다운로드가 느려지는 상황에까지 이르렀습니다. 이를 해결하기 위해 이미 배포된 알파버전을 주기적으로 제거하고, 매번 알파 배포를 하던 것에서 필요한 경우만 배포되도록 작업하고 `package metadata`에서 줄일 수 있는 README 부분과 scripts 부분 등을 배포 전 삭제하는 plugin을 작업하였습니다.

README 내용은 `package metadata`에 매 버전마다 포함됩니다. Scripts 또한 preinstall, postinstall 등이 포함된 경우가 아니라면 배포 시에는 제거해도 되기에 배포 직전 제거합니다.

### 4\. deploy-plugin-bump

모노레포를 운영하면 워크스페이스 의존성은 항상 최신이어서 의존성 버전이 실제보다 낮게 설정되는 경우가 생깁니다. 예시를 보겠습니다. workspace에는 foo와 bar 패키지가 있습니다.
    
    
    .
    ├── foo
    │   └── package.json // 1.0.0
    └── bar
        └── package.json // 1.0.0

foo는 bar에 의존하고 bar에서 제공하는 Feature1을 이용하고 있습니다.
    
    
    {
    	"name": "foo",
    	"version": "1.0.0",
    	"dependencies": {
    		"bar": "workspace:^1.0.0"
    	} 
    }
    
    
    import { Feature1 } from 'bar';

위 상황에서 bar가 1.1.0으로 올라가면서 Feature2를 제공합니다. foo와 bar는 workspace로 연결되어 있기에 ^1.0.0 으로 dependency가 명시되어 있지만 1.1.0이 바로 resolve되고 Feature2가 사용 가능해집니다. 이 경우 foo에서 Feature2를 import하여 이용한다면 workspace에서는 문제가 없습니다.
    
    
    import { Feature1, Feature2 } from 'bar';

하지만 서비스에서는 foo 라이브러리를 이용할 때 `“bar”: "^1.0.0"`으로 명시되어 있기에 bar 1.0.0이 resolve 될 가능성이 있습니다. 이 때 1.0.0이 resolve 된다면 workspace에서는 빌드/테스트도 잘 동작하지만 서비스에서는 문제가 발생할 여지가 생기게 되는 것이지요.

pnpm 에서 제공하는 `workspace:^`, `workspace:*` 을 사용해도 위 문제를 해결할 수 있습니다. 하지만 이런 버전 명시는 배포 시마다 항상 workspace 버전이 명시되어 불필요한 install을 늘리고 workspace package 메이저 업이 있을 때 다른 패키지들이 깨지지 않게 되는 문제가 발생합니다.

이를 해결하기 위해 `deploy-plugin-codegen-since`와 `deploy-plugin-bump`가 등장했습니다.

처음에는 public API들을 잘 관리하기 위해 추가되었던 CodeGen export에서 시작하여 public API들이 어느 버전부터 추가되었는지 알 수 있도록 `deploy-plugin-codegen-since`가 추가되었고 이 덕분에 어떤 API들이 어떤 버전부터 export되었는지 알 수 있게 되어 workspace bump까지 가능해졌습니다.

위 케이스에서 foo가 bar 1.1.0에서 추가된 Feature2를 사용한다면 CI/CD에서 bar에서 사용 중인 api를 모두 뽑고 각 api들이 언제 추가되었는지 확인하고 가장 높은 버전을 `package.json`의 `dependencies` 필드에 자동으로 패치해줄 수 있게 된 것입니다.

## 결론

위에 언급한 예시 외에도 다양한 요구사항을 플러그인으로 구현하여 여러 레포에서 이용하고 있습니다. 많은 팀들이 라이브러리를 관리/운영하실 텐데요. 규모가 커짐에 따라 발생할 수 있는 불편함 들을 노드 챕터에서 풀어낸 방식이 도움이 되었기를 바랍니다.

노드 챕터에는 서술한 내용 외에도 모노레포 관리 노하우가 많이 쌓여있는데요 더 자세한 내용이 궁금하신 분들은 토스 노드 챕터에 지원해주세요.