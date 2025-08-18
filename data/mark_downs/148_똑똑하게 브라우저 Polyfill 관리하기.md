# 똑똑하게 브라우저 Polyfill 관리하기

**Date:** 2023년 1월 21일
**URL:** https://toss.tech/article/smart-polyfills

---

토스 앱은 넓은 범위의 기기를 지원하면서도 현대적인 JavaScript를 이용해서 개발되고 있습니다. 그렇지만 최신 JavaScript를 오래된 브라우저 위에서 실행하기 위해서는 “Polyfill” 문제를 해결해야 하는데요.

이번 아티클에서는 Polyfill 문제가 무엇인지 알아보고, 토스에서 어떻게 똑똑하게 다루고 있는지 살펴보려고 합니다.

## Polyfill이란?

오래된 버전의 브라우저에서는 현재 JavaScript가 당연하게 사용하고 있는 `Promise`나 `Set` 객체가 없는 경우가 있습니다. 편리한 [Array.prototype.at\(\)](https://developer.mozilla.org/ko/docs/Web/JavaScript/Reference/Global_Objects/Array/at) API는 Chrome 92 이상에서만 지원되기도 합니다.

예를 들어서, 아래와 같은 코드는 최신 브라우저에서는 잘 동작하지만, 오래된 브라우저에서는 실패합니다. 객체나 메서드에 대한 구현이 없기 때문이죠.
    
    
    [1, 2, 3].at(-1);
    
    Promise.resolve(1);
    
    new Set(1, 2, 3);

이런 문제를 해결하기 위해서는 오래된 브라우저에서 없는 구현을 채워주어야 합니다. 이렇게 구현을 채워주는 스크립트를 Polyfill이라고 합니다. 대부분의 Polyfill은 아래와 같이 이미 브라우저에 포함되어 있는지 체크하고, 없으면 값을 채워주는 형태로 동작합니다.
    
    
    Array.prototype.at = Array.prototype.at ?? /* Array.prototype.at에 대한 자체 구현 */;
    
    

위 스크립트를 실행한 이후에는, 오래된 브라우저에서도 안전하게 `[1, 2, 3].at(-1)` 코드를 실행할 수 있습니다.

표준적으로 사용되는 Polyfill들은 [core-js 리포지토리](https://github.com/zloirock/core-js)에 모여 있습니다. 아래 코드를 실행하면 대부분의 ECMAScript 표준 객체와 메서드를 오래된 브라우저에서도 사용할 수 있게 됩니다.
    
    
    import 'core-js/actual';

## Polyfill의 문제

위와 같이 코드를 작성하면 폭넓은 브라우저를 지원할 수 있다는 장점이 있지만 문제가 하나 생깁니다. 불러와야 하는 JavaScript 코드가 많아진다는 점입니다. 실행해야 하는 Polyfill 스크립트가 많아질수록 사용자가 경험하는 웹 서비스의 성능은 나빠집니다.

특히, 위와 같이 설정하면 최신 버전의 브라우저에서는 대부분의 ECMAScript 표준 객체와 메서드가 포함되어 있음에도 불구하고 불필요한 Polyfill 스크립트를 내려받아야 합니다. 꼭 필요한 Polyfill 스크립트만 선택적으로 불러올 수 있는 방법은 없을까요?

## 첫 번째 방법: @babel/preset-env 사용하기

이 문제를 해결하기 위해 사용할 수 있는 첫 번째 방법은 [@babel/preset-env](https://babeljs.io/docs/en/babel-preset-env) Smart Preset을 사용하는 것입니다. 이 Smart Preset은 이미 정의된 브라우저 목록에 따라서 자동으로 필요 없는 Polyfill을 제거해 줍니다.

예를 들어서, 웹 페이지가 Internet Explorer 11을 지원해야 한다면 아래와 같이 `babel.config.js` 를 설정할 수 있습니다.
    
    
    module.exports = {
      presets: [
        ['@babel/preset-env', { targets: { ie: 11 } }],
      ],
      /* 그 외의 설정 */
    };
    
    

이후에 동일하게 `core-js/actual` 을 import 하더라도 Internet Explorer 11에 필요한 Polyfill 목록만 포함되는 것을 확인할 수 있습니다. 총 221개의 Polyfill이 포함됩니다.
    
    
    // 입력 코드
    import 'core-js/actual';
    
    
    // 출력 코드
    require("core-js/modules/es.symbol.js");
    require("core-js/modules/es.symbol.description.js");
    require("core-js/modules/es.symbol.async-iterator.js");
    require("core-js/modules/es.symbol.has-instance.js");
    require("core-js/modules/es.symbol.is-concat-spreadable.js");
    require("core-js/modules/es.symbol.iterator.js");
    // ... 계속 (총 221개의 Polyfill)

[Babel playground](https://babeljs.io/repl/#?browsers=ie%2011&build=&builtIns=entry&corejs=3.21&spec=false&loose=false&code_lz=JYWwDg9gTgLgBAcgMbQKYFoBWBnA9AQyRgFd8AbBAbiA&debug=false&forceAllTransforms=false&shippedProposals=false&circleciRepo=&evaluate=false&fileSize=false&timeTravel=false&sourceType=module&lineWrap=true&presets=env&prettier=false&targets=&version=7.20.12&externalPlugins=&assumptions=%7B%7D)

Internet Explorer 11을 지원 브라우저 목록에서 제외하면 훨씬 적은 25개의 Polyfill이 포함됩니다.
    
    
    module.exports = {
      presets: [
        ['@babel/preset-env', { targets: 'defaults, not ie 11' }],
      ],
      /* 그 외의 설정 */
    };
    
    
    // 입력 코드
    import 'core-js/actual';
    
    
    // 출력 코드
    require("core-js/modules/es.error.cause.js");
    require("core-js/modules/es.aggregate-error.cause.js");
    require("core-js/modules/es.array.at.js");
    require("core-js/modules/es.array.includes.js");
    require("core-js/modules/es.object.has-own.js");
    require("core-js/modules/es.regexp.flags.js");
    require("core-js/modules/es.string.at-alternative.js");
    require("core-js/modules/es.typed-array.at.js");
    require("core-js/modules/esnext.array.find-last.js");
    // ... 계속 (총 25개의 Polyfill)
    
    

[Babel playground](https://babeljs.io/repl/#?browsers=defaults%2C%20not%20ie%2011&build=&builtIns=entry&corejs=3.21&spec=false&loose=false&code_lz=E4UwjgrglqAUDkBjA9qAtAKwM4HoCGiALhHgDbwCUA3EA&debug=false&forceAllTransforms=false&shippedProposals=false&circleciRepo=&evaluate=false&fileSize=false&timeTravel=false&sourceType=module&lineWrap=true&presets=env&prettier=false&targets=&version=7.20.12&externalPlugins=&assumptions=%7B%7D)

이렇게 `@babel/preset-env`에 브라우저 지원 범위를 설정하면 Polyfill을 안정적으로 포함하면서 스크립트의 크기를 감축할 수 있습니다.

## 두 번째 방법: User-agent에 따라 동적으로 스크립트 생성하기

Babel을 올바르게 설정함으로써 포함되는 Polyfill 스크립트의 크기를 줄일 수 있지만, 최신 버전의 브라우저에서 불필요한 스크립트를 내려받게 되는 문제는 동일합니다. 예를 들어서, Chrome 최신 버전은 문제없이 `[1, 2, 3].at(-1)` 을 실행할 수 있지만, 관련한 Polyfill 스크립트를 내려받습니다.

이 문제를 해결하는 또다른 방법은 브라우저의 User-agent에 따라서 동적으로 Polyfill 스크립트를 생성하는 것입니다.

예를 들어서, Financial Times에서 관리하고 있는 [polyfill.io](http://polyfill.io/) 서비스에서는 <https://polyfill.io/v3/polyfill.min.js> 라고 하는 경로로 동적인 Polyfill 스크립트를 제공합니다.

최신 버전의 Chrome에서 해당 경로에 접속하면, 아무 Polyfill 스크립트도 내려오지 않는다는 것을 알 수 있습니다.
    
    
    $ curl -XGET "https://polyfill.io/v3/polyfill.min.js" \
       -H "User-Agent: Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Mobile Safari/537.36" \
       -v
    /* 빈 스크립트 */

반대로, Internet Explorer 11에서 실행하면 많은 양의 Polyfill 스크립트가 내려온다는 것을 알 수 있습니다.
    
    
    $ curl -XGET "https://polyfill.io/v3/polyfill.min.js" \
       -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Trident/7.0; rv:11.0) like Gecko" \
       -v
    (function(self, undefined) {!function(t){t.DocumentFragment=function n(){return document.createDocumentFragment()
    
    

이렇게 User-agent에 따라 동적으로 Polyfill 스크립트를 생성하면 최신 브라우저에서는 아무 Polyfill도 내려주지 않고, 오래된 브라우저에서는 필요한 Polyfill 만 내려줄 수 있게 됩니다. ✨ 브라우저가 꼭 필요한 Polyfill 스크립트만 내려받을 수 있는 것이죠.

### 자체 Polyfill 서비스 구축하기

토스에서는 [polyfill.io](http://polyfill.io/) 서비스를 그대로 사용할 수도 있었지만, Financial Times가 제공하는 Polyfill 중 일부가 ECMAScript 표준대로 작동하지 않아 오류가 발생한 경험이 있어서 자체적으로 구현했습니다.

`core-js` 와 `core-js-compat`, `browserslist-useragent` 라이브러리를 사용하면 손쉽게 동적인 Polyfill을 제공하는 Node.js 서버를 만들 수 있었습니다.

먼저, User-agent에 따라서 필요한 core-js polyfill 목록을 계산하기 위해서 아래와 같은 `getCoreJSPolyfillList` 함수를 작성할 수 있습니다.
    
    
    import { resolveUserAgent } from 'browserslist-useragent';
    import compat from 'core-js-compat';
    
    /**
     * userAgent에 따라 필요한 Polyfill의 목록을 반환합니다.
     * e.g. ['es.symbol', 'es.symbol.description', 'es.symbol.async-iterator']
     */
    function getCoreJSPolyfillList(userAgent: string) {
      try {
        const result = resolveUserAgent(userAgent);
        const majorVersion = parseMajorVersion(result.version);
    
        return compat({
          targets: `${result.family} >= ${majorVersion}`,
          version: coreJSVersion,
        }).list;
      } catch {
        // 일반적이지 않은 User-Agent인 경우
        return compat({
          targets: 'IE >= 11',
          version: coreJSVersion,
        }).list;
      }
    }
    
    function parseMajorVersion(versionString: string) {
      const match = versionString.match(/^(\\d+)\\.*/);
    
      if (match == null) {
        return versionString;
      }
    
      return match[1];
    }
    
    

이제 필요한 Polyfill 리스트를 하나의 스크립트로 만들면 됩니다. 토스에서는 `esbuild` 를 이용하여 core-js 스크립트를 하나로 이어붙이는 방법을 선택했습니다.
    
    
    import { build } from 'esbuild';
    
    /*
     * userAgent에 맞는 완성된 Polyfill 스크립트를 생성한다.
     */
    async function buildPolyfillScript(userAgent: string) {
      const script = getCoreJSPolyfillScript(userAgent);
    
      const result = await build({
        stdin: {
          contents: script,
          loader: 'js',
        },
        target: 'es5',
        bundle: true,
        minify: true,
        write: false,
      });
    
      return result.outputFiles[0].contents;
    }
    
    function createCoreJSPolyfillScript(userAgent: string) {
      return getCoreJSPolyfillList(userAgent)
        /* 실험적인 esnext 기능은 제외합니다. */
        .filter(x => !x.startsWith('esnext.'))
        .map(item => `import "core-js/modules/${item}";`)
        .join('\\n');
    };
    
    

이제 이 함수를 Node.js 서버에 포함시키거나, Lambda@Edge, Compute@Edge 와 같은 Edge Runtime에 포함하면 손쉽게 나만의 Polyfill 서버를 띄울 수 있습니다.

## 마치며

토스팀에서는 자체 제작한 Polyfill 시스템을 이용하여 최신 JavaScript API는 마음껏 활용하면서도 오래된 버전의 브라우저도 빠짐없이 지원할 수 있었습니다.

글을 마무리하면서, 글의 내용을 요약해보자면 아래와 같습니다.

  * Polyfill이란 신규 JavaScript API를 오래된 버전의 브라우저에서도 사용할 수 있도록 하는 방법입니다. 그렇지만, Polyfill 스크립트가 많아지면 웹 성능이 나빠집니다.
  * Babel의 @babel/preset-env 스마트 프리셋을 이용하여 포함할 Polyfill 스크립트의 범위를 지정할 수 있습니다. 다만, 이 경우에도 최신 브라우저는 오래된 브라우저를 위한 Polyfill을 내려받습니다.
  * User-agent에 따라 동적으로 Polyfill 스크립트를 생성할 수 있습니다. 이로써 최신 브라우저에서 내려받는 Polyfill 스크립트를 거의 없게 만들 수 있습니다.