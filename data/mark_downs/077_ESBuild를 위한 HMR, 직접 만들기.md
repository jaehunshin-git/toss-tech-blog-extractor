# ESBuild를 위한 HMR, 직접 만들기

**Date:** 2025년 3월 18일
**URL:** https://toss.tech/article/frontend-esbuild-hmr

---

토스 기술 조직의 각 챕터는 라이트닝 토크에서 다양한 주제에 대한 인사이트와 아이디어를 자유롭게 공유합니다. 기록을 통해 생생한 라이트닝 토크 현장을 함께 느껴보세요\!

#### 이번 라이트닝 토크에서 다루는 내용 \- HMR\(Hot Module Replacement\)의 개념과 동작 원리 \- Metro, Webpack, Vite 등 다양한 번들러의 HMR 구현 방식 비교 \- ESBuild 기반 번들러에서 HMR 구현 시 해결해야 할 과제들 \- 런타임 모듈 접근, 의존성 그래프 구축, 파일 변경 감지 등 핵심 구현 전략

프론트엔드 개발을 하면서 좋은 개발 경험이 무엇인지 고민해 보신 적 있으신가요? 요즘 우리는 이미 좋은 환경에서 개발하고 있다고 생각하는데요. 코드 가독성과 일관성을 위한 포맷터와 린터, 복잡한 구현 없이 사용할 수 있는 번들러, 강력한 디버깅 도구들이 모두 우리의 개발 경험에 기여하고 있죠.

이번 시간에는 그 중에서도 제가 생각하는 가장 편한 기능을 소개해 보려고 해요. 개발자라면 누구나 한 번쯤 ‘이거 진짜 편하네\!’라고 감탄했던 경험이 있을 겁니다. 바로 HMR\(Hot Module Replacement\)인데요. 코드를 수정하고 저장했을 때, 페이지를 새로고침하지 않아도 변경사항이 즉시 반영되는 기능이죠. 프론트엔드 개발에서는 빠른 피드백 루프가 곧 생산성으로 연결되기 때문에, HMR은 개발자 경험을 혁신하는 핵심 기능 중 하나예요. 웹 개발뿐 아니라 React Native 환경에서도 널리 사용되고 있고요.

그럼 먼저 HMR이 어떤 원리로 동작하는지, 그리고 Metro, Webpack, Vite, ESBuild 같은 다양한 번들러가 HMR을 어떻게 지원하는지 살펴볼게요. 그런 뒤, 제가 ESBuild 기반 번들러를 어떻게 만들었는지 그 과정을 소개해 볼게요.

## HMR이란

HMR은 변경된 코드 조각만 런타임에서 동적으로 교체하는 기능이에요. HMR이 적용되어 있다면 페이지를 새로고침하지 않고도 코드 수정 사항이 즉시 반영돼요. 우리의 일반적인 개발 플로우를 떠올려볼까요?

  1. 코드를 작성하고 저장한다.
  2. 페이지를 새로고침하지 않아도 코드가 반영된다.
  3. 브라우저 또는 React Native 앱에서 즉시 변경된 내용을 확인한다.

이 과정에서 가장 큰 장점은 상태를 유지하면서도 코드 변경을 반영할 수 있다는 것입니다. 전체 페이지를 새로고침하면 폼 입력값이나 UI 상태가 초기화되어 불편한데요. HMR을 활용하면 이러한 불편 없이 변경을 확인할 수 있어요.

## 번들러별 HMR 구현 방식

이 HMR 기능은 번들러마다 서로 다른 방식으로 구현되어 있는데요. 대표적인 번들러들의 HMR 구현 방식을 알아볼게요.

### Metro: React Native 기본 번들러

Metro는 React Native 환경에서 HMR을 지원하는 기본 번들러인데요. 핵심 원리는 모듈을 전역에 등록한 뒤, 변경된 모듈만 교체하는 방식입니다.

  * 코드가 변경되면, 해당 모듈의 고유 ID를 찾아 업데이트합니다.
  * 전체 앱을 다시 실행할 필요 없이, 변경된 부분만 새로운 코드로 교체됩니다.

다음은 Metro의 HMR 지원을 위한 코드 일부예요.
    
    
    (function (global) {
      global[`${__METRO_GLOBAL_PREFIX__}__d`] = define;
    
      function define(factory, moduleId, dependencyMap) {
        modules.set(moduleId, { factory, dependencyMap, isInitialized: false, publicModule: { exports: {} } });
      }
    })(typeof globalThis !== 'undefined' ? globalThis : this);

Metro는 HMR을 위해 코드를 다음과 같이 변환해요. `__d`라는 함수를 사용해서 각 모듈에 고유한 ID를 부여하고, 이 ID를 이용해 런타임에서 모듈을 참조할 수 있도록 하는 거죠. 중요한 점은 모듈이 런타임에서 교체 가능한 상태로 등록된다는 점입니다. 이 방식 덕분에 React Native 개발 시 빠른 코드 반영이 가능해져요. 
    
    
    // message.js
    export const message = 'Hello, world!';
    
    // App.js
    import { message } from './message';
    import logo from './logo.svg';
    import './App.css';
    
    function App() {
    	return (
    		<div className="App">
    			<header className="App-header">
    				<img src={logo} className="App-logo" alt="logo" />
    				<h1>{message}</h1>
    			</header>
    		</div>
    	);
    }
    
    export default App;

아래 변환된 코드를 보면 중간에 모듈 ID가 배열에 들어가 있어요.
    
    
    __d(function (global, _$$_REQUIRE, _$$_IMPORT_DEFAULT, _$$_IMPORT_ALL, module, exports, _dependencyMap) {
      var _reactNative = _$$_REQUIRE(_dependencyMap[0], "react-native");
    
      function App() {
        // ...
      }
    
      var _default = exports.default = App;
    }, 0, [1, 104, 631, 589], "index.js"); // 모듈의 ID 모음
    
    __d(function (global, _$$_REQUIRE, _$$_IMPORT_DEFAULT, _$$_IMPORT_ALL, module, exports, _dependencyMap) {
      Object.defineProperty(exports, "__esModule", {
        value: true
      });
      exports.message = void 0;
      var message = exports.message = 'Hello, world!';
    }, 631, [], "message.js", {"0":[],"631":[0]});

### Webpack: 전통적인 HMR 방식

Webpack도 Metro와 유사하게 런타임에 모듈을 등록한 뒤 관리하는 구조인데요. 전역 객체\(`__webpack_modules__`\)를 활용해 변경된 모듈만 교체하는 방법을 사용해요.

  1. 변경된 모듈을 감지하면, 서버가 새로운 코드 조각을 생성합니다.
  2. 클라이언트에서 기존 모듈을 대체하는 방식으로 업데이트합니다.
  3. 의존성 그래프를 추적하여 변경된 모듈을 참조하는 모든 상위 모듈도 갱신됩니다.

다음은 Webpack의 HMR 지원을 위한 코드 일부예요.
    
    
    var __webpack_modules__ = {
      './src/App.js': (module, __webpack_exports__, __webpack_require__) => {
        // ...
      },
      '...': (module, __webpack_exports__, __webpack_require__) => {
        // ...
      },
    };

HMR은 이렇게 등록된 모듈을 런타임에서 직접 참조하거나 교체하는 식으로 동작해요.

### Vite: 네이티브 ESM을 활용한 HMR

모던 번들러 중 하나인 Vite는 브라우저의 네이티브 ESM\(ES Modules\)을 최대한 활용해, 불필요한 런타임 로직 없이 HMR을 구현합니다.

  * 변경된 모듈의 URL에 타임스탬프를 추가해 브라우저 캐시를 무효화합니다.
  * 필요한 모듈만 다시 불러오기 때문에 빠르고 간단하게 HMR이 동작합니다.

예를 들어, `foo.ts` 파일을 변경하면 import 경로 뒤에 타임스탬프가 붙어 새로운 모듈로 로드돼요.
    
    
    import { foo } from './foo.ts?t=1708957319787'

이렇게 간단하게 구현되어 있어서 다른 방식에 비해 상대적으로 복잡도가 낮다는 장점이 있어요.

### ESBuild

ESBuild는 초고속 번들링을 목표로 개발된 번들러이기 때문에, 기본적으로 HMR 기능을 제공하지 않아요. 하지만 토스에서는 ESBuild를 기반으로 한 React Native 번들러를 사용하고 있어서 HMR 기능을 자체적으로 구현했어요.

## ESBuild 기반 번들러에서 HMR 구현하기

토스에서는 빠른 빌드 속도를 위해 ESBuild 기반 번들러를 사용하고 있어요. 하지만 HMR이 지원되지 않아 불편함이 있었죠. 개발 편의성도 놓칠 수 없었기에, HMR 기능을 직접 구현했어요. 구현 과정에서 해결해야 했던 주요 과제들을 살펴볼게요.

### 1\. 런타임 모듈 접근 구현

HMR을 구현하려면 먼저 런타임 환경에서 모듈을 참조하거나 등록할 수 있는 구조가 필요합니다. ESBuild가 생성하는 번들은 이런 구조를 제공하지 않기 때문에, [SWC](https://swc.rs/) 플러그인을 구현해서 코드를 변환했어요.

예를 들어, 다음과 같은 원본 코드가 있다면,
    
    
    import foo from './foo';
    export function something() {
      return foo.value;
    }

아래와 같이 변환했는데요. 변경된 코드 조각만 변환 및 교체할 수 있도록 처리한 거예요. 런타임에서 모듈을 참조하거나 교체할 수 있도록 `global.__modules`에 필요한 기능을 구현했어요.
    
    
    import foo from './foo';
    
    global.__modules.define(function (__ctx) {
      var { default: foo } = __ctx.require('/path/to/foo.ts');
      var __x = function something() {
        return foo.value;
      }
      __ctx.exports(function () {
        return { something: __x };
      });
    }, '/path/to/module.ts', __deps);
    
    var __deps = {
      '/path/to/foo.ts': function () {
        return { default: __x };
      };
    };
    var __x;
    
    export { __x as something };

`import`, `export` 구문이 유지되기 때문에 모듈에 대한 처리는 번들러\(ESBuild\)에 전적으로 위임하고, 모듈에서 `export` 하는 대상의 레퍼런스만 등록하는 과정이에요.

#### 런타임 환경에서는 \(ESM\) import, export / \(CommonJS\) require, module 구문을 사용할 수 없기 때문에, 등록된 모듈을 전역에서 참조하는 형태로 변환해요.

### 2\. 고유 모듈 식별자 생성

하지만 여기서 필요한 값이 있는데요, 그것은 바로 모듈을 식별하기 위한 ID 값이에요. 모듈을 식별하기 위한 고유한 값이 있어야 런타임에서 모듈을 참조할 수 있게 될 테니까요.

많은 번들러들이 그렇듯이 ESBuild 번들러 내부에서도 이러한 정보를 수집하고 있는데요, 아쉽게도 플러그인 API에서 접근할 수 있는 방법은 제공되지 않았어요.

다음 다이어그램은 ESBuild 리포지토리에 게시된 [Architecture](https://github.com/evanw/esbuild/blob/main/docs/architecture.md) 자료의 일부인데요. 모듈 해석 과정을 살펴보면, 모듈을 로드하고 AST 분석을 거친 뒤, 참조하고 있는 다른 모듈의 경로를 해석하는 구조로 동작하는 것을 알 수 있어요.

이 말은, 비록 ESBuild 내부 종속성 그래프에 직접 접근할 수는 없지만 다음과 같이 모듈을 식별할 수 있는 고유한 값\(Resolved path\)을 알아낼 수 있다는 의미예요.

그래서 다음과 같이 ESBuild의 `onLoad` 훅에서 넘어오는 `args.path`를 모듈 ID로 활용하기로 했어요. 이 값은 모듈의 절대 경로로, 각 모듈을 고유하게 식별할 수 있어요.
    
    
    const plugin: Plugin = {
      name: 'example-plugin',
      setup(build) {
        build.onLoad({ filter: /\.([mc]js|[tj]sx?)$/ }, (args) => {
          const moduleId = args.path; // 🎉
          
          // ...
        });
      },
    };

### 3\. 모듈 의존 관계 추적

번들러는 코드 스플리팅이나 트리 쉐이킹과 같은 최적화를 위해 모듈 간의 의존 관계를 추적하는데, HMR도 이런 정보가 필요하답니다. 특정 모듈이 변경됐을 때, 해당 모듈을 참조하는 다른 모듈들에도 변경 사항이 전파되어야 하기 때문이죠. 이때 의존성 그래프가 있다면 쉽게 추적할 수 있어요.

ESBuild 번들러의 [구현체](https://github.com/evanw/esbuild/blob/v0.25.0/internal/bundler/bundler.go#L2232)를 잠시 살펴보면, 번들링 과정에서 수집한 모듈 정보\(Path 등\)를 Metafile 형식으로 기록해주는 것을 알 수 있어요.

다음과 같은 모듈 코드가 있을 때 생성되는 Metafile 데이터는 아래 코드와 같아요.
    
    
    // index.ts
    import './foo';
    import './bar';
    import './baz';
    
    // ...
    
    
    // Metafile 데이터
    {
      "inputs": {
        "/path/to/index.ts": {
          "bytes": 123,
          "imports": [
            {
              "path": "/path/to/foo.ts",
              "original": "./foo",
              "type": "import-statement"
            },
            {
              "path": "/path/to/bar.ts",
              "original": "./bar",
              "type": "import-statement"
            },
            {
              "path": "/path/to/bar.ts",
              "original": "./baz",
              "type": "import-statement"
            }
          ]
        },
        "/path/to/foo.ts": { /* ... */ }
        "/path/to/bar.ts": { /* ... */ }
        "/path/to/baz.ts": { /* ... */ }
      },
      "outputs": { /* ... */ }
    }

번들에 포함되어있는 모든 모듈이 나열되어있을 뿐만 아니라, 각 모듈에서 참조하고 있는 모듈들의 정보까지 함께 포함되어있는 것을 확인할 수 있는데요. 이 데이터를 잘 정제하면 의존성 그래프로 충분히 활용할 수 있었죠.

그래서 ESBuild의 `metafile` 옵션을 활용해 의존성 그래프를 구축했어요. 다음과 같이 어떤 모듈이 어떤 모듈에 의존하는지, 또 어떤 모듈에 의해 참조되는지 추적할 수 있었죠.
    
    
    {
      "inputs": {
        "/path/to/index.ts": {
          "imports": [
            { "path": "/path/to/foo.ts", "original": "./foo" },
            // 다른 import 항목들...
          ]
        },
        // 다른 모듈들...
      }
    }
    
    

### 4\. 파일 변경 감지 구현

HMR이 트리거되는 시점은 파일이 저장되거나 추가/삭제될 때인데요. 이때 어떤 일이 일어나야 할까요?

  1. 먼저 번들러에서 파일이 변경되었음을 감지하고
  2. 변경된 파일\(모듈\)을 새로 변환\(Transform\)해서 런타임 환경으로 전달한 뒤
  3. 런타임에서는 받아온 코드를 평가\(Evaluate\)하여 변경 사항을 반영해야 합니다.

모듈이 런타임에 교체될 때는 위와 같은 절차를 거쳐요. 즉, HMR 기능을 트리거 하기 위해 가장 먼저 필요한 것은 파일이 변경되었음을 감지하는 것이죠.

ESBuild의 [watch 모드](https://esbuild.github.io/api/#watch)는 단순히 빌드를 새로 트리거할 뿐, 어떤 파일이 변경되었는지 알려주지 않기 때문에, 별도의 파일 감지 기능을 구현했어요.
    
    
    const subscription = await watcher.subscribe(projectPath, (error, events) => {
      events.forEach((event) => {
        // 의존성 그래프 업데이트 및 HMR 트리거
        switch (event.type) {
          case 'create':
            // ...
    
          case 'update':
            // ...
          
          case 'delete':
            // ...
        }
      });
    });

이렇게 모듈이 새로 추가되거나 수정, 삭제될 때 이벤트를 받아 종속성 그래프에 상태를 업데이트해 주는 방식으로 실제 파일 시스템상의 모듈과 종속성 그래프 간의 상태를 일치시킬 수 있었어요.

### 5\. 모듈 변환 및 교체

마지막으로 새로 추가되거나, 수정된 모듈의 경우 참조하고 있는 의존성도 다시 한 번 검증해야 하는데요, 다음과 같은 케이스를 고려해야 해요.

그래프에 없는 모듈이 추가되는 경우 \(파일 추가\)그래프에 있는 모듈이 업데이트될 때 \(파일 수정, 의존성이 빠지거나 / 추가되는 상황\)

정확한 그래프 정보를 만들려면 모든 케이스에서 파일을 읽어 실제로 참조하고 있는 모듈\(Dependency\) 정보들을 수집해야 하죠.

다음과 같이 특정 파일이 변경되면, 해당 모듈을 읽어서 런타임에서 교체할 수 있는 형태로 변환한 후, 웹소켓을 통해 클라이언트에 전송해요.
    
    
    fs.readFile(event.path, 'utf-8').then((code) => {
      const hmrChunk = transformHMRChunk(code, dependencies);
      socket.send(JSON.stringify({
        type: 'update',
        path: event.path,
        code: hmrChunk,
        // 변경된 모듈로 인해 영향을 받는 다른 모듈 정보들
        inverseDependencies: graph.inverseDependenciesOf(event.path)
      }));
    });

클라이언트에서는 다음과 같이 이 코드를 평가해서 모듈을 교체해요.
    
    
    try {
      eval(message.code);
      for (const id of message.inverseDependencies) {
        // 영향을 받는 다른 모듈들을 재평가(Re-evaulate) 하여 변경 사항 전파
        global.__modules.apply(id);
      }
    } catch (error) {
      console.error(`[HMR] 모듈 교체 실패`);
      // 전체 앱 reload 등 대체 처리
    }

### 6\. React 환경을 위한 추가 구현

React 환경에서는 단순히 모듈을 교체하는 것만으로는 변경 사항이 반영되지 않아서 React의 내부 상태를 조작해야 하는데요. 이를 위해 `react-refresh` 라이브러리를 활용했어요.

먼저 React 컴포넌트를 빌드할 때 다음과 같이 변환했습니다.
    
    
    var _s = $RefreshSig$();
    function App() {
      _s();
      // 컴포넌트 코드...
    }
    _s(App, "A3WfNgzdYyyhx8+TirhyDvdPM54=");
    $RefreshReg$(App, "App");

이렇게 하면 컴포넌트의 시그니처를 추적하고, 시그니처가 변경되지 않았을 때는 상태를 유지한 채 리렌더링할 수 있어요.

### 7\. 증분 빌드 구현

마지막으로, 전체 앱이 새로고침 될 때를 대비해 증분 빌드\(Incremental build\)를 구현했습니다. 증분 빌드란 전체 코드를 다시 빌드하지 않고, 변경된 부분만 빌드하는 최적화 기법이에요.
    
    
    const context = await esbuild.context(options);
    // 모듈 변경 시
    result = await context.rebuild();

ESBuild에서 증분 빌드 API\(rebuild\)를 제공하는데요. 저희처럼 플러그인을 쓴다면 이 API와 별개로 직접 처리를 해줘야 해요. 그래서 플러그인에서 파일 변경 시간을 기반으로 [캐싱](https://esbuild.github.io/plugins/#caching-your-plugin)을 구현했어요.

## 결과

이렇게 구현한 HMR 시스템으로, 토스의 React Native 개발 환경에서도 빠른 빌드 속도와 실시간 코드 반영의 편리함을 동시에 누릴 수 있게 되었습니다. 

다음 데모에서 볼 수 있듯이 코드를 수정하면 즉시 앱에 반영되고, 컴포넌트의 상태도 유지됩니다.

앱 전체 새로고침 대신 상태가 유지된채 변경 사항이 반영됨

## 마무리하며

오늘은 이렇게 HMR에 대해 알아보고, ESBuild 기반 번들러에서 HMR을 구현하는 여정을 간략히 소개해 봤는데요. 모든 내용을 다루기에는 시간이 부족했네요. 그래도 핵심 아이디어는 잘 전달되었으리라 생각합니다.

더 자세한 내용이 궁금하시거나 질문이 있으시다면, 언제든지 알려주세요. 감사합니다\!

Talk 이근혁 Edit 한주연