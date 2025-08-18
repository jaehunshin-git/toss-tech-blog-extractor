# Node.js url.parse() 취약점 컨트리뷰션

**Date:** 2023년 5월 12일
**URL:** https://toss.tech/article/nodejs-security-contribution

---

토스 보안기술팀\(Security Tech\)에서는 개발 서비스 외에도 회사에서 사용하는 프레임워크나 Third-party 시스템의 취약점을 연구하고 있어요.

이번 아티클에서는 Node.js의 Built-in API 중 하나인 `url.parse()` 의 Hostname Spoofing 취약점을 발견하고 안전한 코드로 패치될 수 있도록 컨트리뷰션 했던 과정을 다뤄보려 합니다.

<https://github.com/nodejs/node/pull/45011>

## url.parse\(\) 취약점 발생 원인

Node.js의 `url.parse()`는 WHATWG URL API가 아닌 자체적인 스펙으로 개발된 함수에요.

#### WHATWG URL API `WHATWG`는 Web Hypertext Application Technology Working Group의 약어로 국제 웹 표준화 그룹을 뜻해요. WHATWG URL API 는 국제 표준 스펙으로 URL\(Uniform Resource Locator\)을 다룰 수 있도록 제공되는 API입니다. 

WHATWG URL API가 등장하기 전에 자체적으로 개발된 URL 파싱 함수로 보이는데요. 표준 스펙이 아니다 보니 다른 파서\(parser\)와 결과가 다르고, 이 때문에 예상하기 어려운 코드 흐름도 발생했어요.

`url.parse()`에서는 hostname을 잘못된 방식으로 파싱하는 취약점이 있었는데요. 아래 보이는 Node.js [url 라이브러리](https://github.com/nodejs/node/blob/v19.0.1/lib/url.js)의 `getHostname()` 함수에서 발생했어요.
    
    
    /* comment
    해당 취약점은 v19.1.0에서 패치되었습니다. 
    아래 코드는 v19.1.0 이전 버전에서 확인할 수 있습니다.
    */
    function getHostname(self, rest, hostname) {
      for (let i = 0; i < hostname.length; ++i) {
        const code = hostname.charCodeAt(i);
        const isValid = (code >= CHAR_LOWERCASE_A && code <= CHAR_LOWERCASE_Z) ||
                        code === CHAR_DOT ||
                        (code >= CHAR_UPPERCASE_A && code <= CHAR_UPPERCASE_Z) ||
                        (code >= CHAR_0 && code <= CHAR_9) ||
                        code === CHAR_HYPHEN_MINUS ||
                        code === CHAR_PLUS ||
                        code === CHAR_UNDERSCORE ||
                        code > 127;
    
        // Invalid host character
        if (!isValid) {
          self.hostname = hostname.slice(0, i);
          return `/${hostname.slice(i)}${rest}`;
        }
      }
      return rest;
    }

`getHostname()` 함수의 로직은 단순해요. 반복문으로 전달된 문자열의 문자를 하나씩 가져온 뒤, `isvalid` 조건에 맞는 값을 구하는 로직인데요. 조건에 맞지 않는 문자가 발견되면, 이전 문자까지 문자열을 slice하고 hostname으로 설정해요. 그 뒤로 오는 문자들은 모두 path로 설정하고요.

`isValid` 의 조건을 정규식으로 표현해보면 `/[a-zA-Z0-9\.\-\+_]/u` 와 같은데요\(ECMAScript 기준\). “hostname으로는 저 범위의 문자들만 올 수 있어\!”라고 설정해둔 것이죠. hostname에 올 수 없는 문자열은 모두 path로 정의하고요.

디버깅 코드

`getHostname()` 함수에 디버깅 코드를 추가해보면, 실제로 `isValid` 조건에 해당하지 않는 문자가 반복문에 오면, hostname 파싱을 중단해요. 나머지 문자열은 앞에 `/` 를 붙여 path로 사용하고요.

그래서 `http://EVIL_DOMAIN*.toss.im` 의 hostname이 `EVIL_DOMAIN` 이 되어버리면서 Hostname Spoofing 취약점이 발생해요.

#### Hostname Spoofing Hostname Spoofing은 시스템을 대상으로 Hostname을 속이는 해킹 기법을 말합니다. Spoofing은 ‘속이다’라는 사전적 의미를 갖고 있으며, 시스템을 대상으로 어떠한 정보를 속이는 해킹 기법을 Spoofing이라고 합니다.

### WHATWG URL API ↔ url.parse\(\) 비교

반면 WHATWG URL AP 의 hostname 파싱 결과는 `evil_domain*.toss.im` 입니다. 

### Reserved Characters

Node.js에서 hostname을 왜 이렇게 파싱할까요? [RFC 3986](https://www.rfc-editor.org/rfc/rfc3986)는 `Standard URI Syntax` 를 정의해둔 문서인데요. 2.2 Reserved Characters를보면 그 이유를 찾을 수 있어요.

<https://www.rfc-editor.org/rfc/rfc3986#section-2.2>

Reserved Characters는 URI를 구성할 수 있으면서 특수 목적을 가진 문자가 예약된 것입니다. 예시로는 port 구분자로 사용되는 `: `또는 path 구분자로 사용되는 `/`가 있어요. 따라서, `*`, `!`, `$`, `:`, `#` 와 같은 문자들은 hostname으로 사용할 수 없습니다. 정의된 문자들은 `gethostName()`의 `isValid` 조건과 비슷하죠.

## 취약점 악용 시나리오

이러한 WHATWG URL API ↔ `url.parse()` 간 파싱 결과 차이는 서비스의 도메인 검증로직을 우회하는데 악용할 수 있어요. 간단한 예시를 함께 살펴볼게요.
    
    
    // server.ts (exec command: ts-node server.ts)
    /* dependencise
    	express@^4.18.1
    	ts-node@^10.9.1
    	typescript@^4.3.2
    	node-fetch@2
    	@types/node-fetch@^2.6.2
    */
    import express, { Request, Response, NextFunction } from 'express';
    
    const node_fetch = require("node-fetch");
    const app = express();
    
    app.get("/image/resize", async (req: Request, res: Response) => {
    	// GET메소드로 url파라미터 입력 받음
    	const url = req.query.url as string; 
    	// WHATWG URL API를 이용해 hostname 파싱
    	const host = new URL(url).hostname; 
    
    	// 파싱한 hostname 검증 (example.com과 *.example.com일 경우에만 분기문 통과)
    	if(host === "toss.im" || host.endsWith(".toss.im")) { 
    		// 검증된 hostname일 경우, node_fetch로 http request
    		var result = await node_fetch.default(url); 
    		var requestUrl = result.url; 
    		// 파라미터로 입력된 url과 node_fetch로 실제 요청한 url 콘솔 출력
    		console.log(`Input URL: ${url} / Request URL: ${requestUrl}`);
    	// 그 외 경우는 reject
    	} else {
    		console.log("reject");
    	}
    });
    
    app.listen(4540, () => {
    });

위 코드는 파라미터로 URL을 입력받고, 입력된 URL을 검증 후 fetch하는 간단한 웹서버인데요. WHATWG URL API로 hostname을 가져온 뒤, `toss.im` 과 일치하거나 `.toss.im` 으로 끝나는지 도메인을 검증해요.

파라미터로 입력한 url과 node-fetch에서 실제로 요청한 URL 콘솔 출력

URL 파라미터 값을 `https://google.com!.toss.im` 로 입력하면 검증 로직이 우회되고 서버는 `https://google.com/!.toss.im/` 으로 요청하게 되는데요. 그 이유는 아래 `node-fetch` 라이브러리 코드를 보면 알 수 있어요.
    
    
    /* node-fetch v2.6.11 
     * [https://github.com/node-fetch/node-fetch/tree/v2.6.11]
     * request.js
     *
     * Request class contains server only options
     *
     * 
     */
    
    import Url from 'url'; // [1]
    import Stream from 'stream';
    import whatwgUrl from 'whatwg-url';
    import Headers, { exportNodeCompatibleHeaders } from './headers.js';
    import Body, { clone, extractContentType, getTotalBytes } from './body';
    
    const INTERNALS = Symbol('Request internals');
    const URL = Url.URL || whatwgUrl.URL;
    
    // fix an issue where "format", "parse" aren't a named export for node <10
    const parse_url = Url.parse; // [2]
    const format_url = Url.format;
    
    /**
     * Wrapper around `new URL` to handle arbitrary URLs
     *
     * @param  {string} urlStr
     * @return {void}
     */
    function parseURL(urlStr) {
    	/*
    		Check whether the URL is absolute or not
    
    		Scheme: https://tools.ietf.org/html/rfc3986#section-3.1
    		Absolute URL: https://tools.ietf.org/html/rfc3986#section-4.3
    	*/
    	if (/^[a-zA-Z][a-zA-Z\d+\-.]*:/.exec(urlStr)) {
    		urlStr = new URL(urlStr).toString() // [3]
    	}
    
    	// Fallback to old implementation for arbitrary URLs
    	return parse_url(urlStr); // [4]
    }

위 코드는 `node-fetch` 라이브러리에서 URL을 파싱하는 코드 부분입니다. 중요한 부분은 주석으로 번호 표시를 해두었는데요.

  * \[1\] Node.js의 url 라이브러리를 가져옵니다.
  * \[2\] Node.js의 `url.parse()`함수를 `parse_url` 변수에 저장합니다.
  * \[3\] 파싱할 URL이 `/^[a-zA-Z][a-zA-Z\d+\-.]*:/` 정규식 조건과 일치하면 WHATWG URL API로 파싱합니다.
  * \[4\] 그 외에 경우는 Node.js의 `url.parse()`함수로 파싱합니다.

`https://google.com!.toss.im` 은 \[3\]정규식 조건에 충족되지 않으니, \[4\]`url.parse()`로 hostname이 파싱되었고 Node.js의 잘못된 파싱 방식으로 인해 검증 로직이 우회된 것이죠.

이런 예시와 같이 서비스 서버의 검증 로직을 우회하고 공격자가 원하는 임의의 도메인으로 요청하도록 하는 공격기법을 SSRF\(Server Side Request Forgery\)라고 하는데요. 공격자는 SSRF 공격을 통해 외부에 공개되어 있지 않은 서비스 내부 망에 접근하여 민감한 정보들을 탈취하거나, 관리자 기능들을 악용할 수 있어요.

## 취약점 패치 컨트리뷰션

화이트해커 문화에는 취약점을 제보하고 그에 따른 보상을 받는 버그바운티\(Bug Bounty\) 프로그램이 있어요. 보안에 중요한 가치를 두고 있는 기업들이 독립적으로 운영하거나 국가기관에서 운영하기도 하는데요. 토스에서도 작년에 [토스 버그바운티 챌린지](https://bugbounty.toss.im/)를 진행한 바 있고, 국가 기관에서는 한국인터넷진흥원\([KISA](https://knvd.krcert.or.kr/index.do)\)이 국내 소프트웨어에 대한 취약점을 제보받고 있어요.

토스 버그바운티 챌린지

저 또한 버그바운티 프로그램을 통해 Node.js 측에 취약점을 제보하였고, 취약점을 알맞게 패치할 수 있는 방안들에 대해 논의하면서 컨트리뷰션을 시작했어요.

Node.js url.parse\(\) 취약점 제보

기존에 `Unreserved Characters` 를 화이트리스트로 처리하는 방식 대신 `Reserved Characters` 를 블랙리스트로 처리하는 방식으로 변경하여 `isValid` 조건을 좀 더 엄격하게 가져가도록 패치했어요.

패치된 코드는 [Pull Request](https://github.com/nodejs/node/pull/45011)에서 확인할 수 있고, 해당 Pull Request는 `v19.1.0`, `v18.13.0` 에서 적용됐어요.

추가로 기존에 Legacy 상태였던 `url.parse()`함수를 Deprecated로 변경하였는데요. `--pending-deprecation` 옵션을 사용하는 경우, 런타임에서 Deprecated 함수임을 경고하도록 패치되었습니다.

<https://nodejs.org/api/url.html#urlparseurlstring-parsequerystring-slashesdenotehost>

이 글을 읽으신 분들도 Node.js를 사용하고 계시다면, 취약점이 존재하는 버전을 사용 중인지 확인해보세요.*취약점은 `v19.1.0`, `v18.13.0` 에서 패치되었습니다.

그리고 저희 보안기술팀\(Security Tech\)에서 이와 같은 보안 연구를 같이 해나갈 동료분들을 찾고 있습니다. 관심이 있으시다면 [언제든지 문을 두드려 주세요](https://toss.im/career/job-detail?job_id=4555752003&company=%ED%86%A0%EC%8A%A4&detailedPosition=%EB%AA%A8%EC%9D%98%ED%95%B4%ED%82%B9%2F%EC%B7%A8%EC%95%BD%EC%A0%90%20%EB%B6%84%EC%84%9D)\!