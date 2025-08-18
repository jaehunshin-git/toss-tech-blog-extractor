# Reactor Netty Memory Leak 이슈 탐방기

**Date:** 2023년 12월 11일
**URL:** https://toss.tech/article/reactor-netty-memory-leak

---

토스의 백엔드로 오는 요청은 모두 Spring Cloud Gateway 기반의 API Gateway를 통해 클러스터로 들어와요. 그리고 클러스터 안에서는 수많은 서버들이 Spring WebClient를 통한 REST API로 통신해 요청을 처리해요.

최근 두 가지 도구에서 동일한 Memory Leak 이슈를 경험했는데요. 원인이 같았습니다. 문제 원인을 찾은 과정과 그 내용을 공유드릴게요.

### 1\. Spring Cloud Gateway Memory Leak 이슈 파악하기

어느 날 한 게이트웨이로부터 OOMKilled 알림을 받았습니다. OOMKilled 알림은 OS가 프로세스를 죽였다는 알림인데요. 해당 컨테이너에 지정된 메모리 상한을 컨테이너가 사용하는 총 메모리가 초과했음을 뜻해요. 죽은 게이트웨이에는 최근에 변경된 사항이 없었고, 게이트웨이가 OOM으로 죽은 적이 처음이라 의아한 상황이었어요. 그래서 하나하나 증거를 살펴보기로 했습니다.

우선 컨테이너가 OOMKilled로 죽었다는 것은 JVM에서 일반적으로 사용하는 Heap 영역의 문제일 가능성이 거의 없습니다. 토스에서는 메모리 할당에 드는 오버헤드를 최대한 줄이기 위해 `-XX:+AlwaysPreTouch` JVM 옵션을 사용하고 있는데요. 이 옵션을 사용하면 어플리케이션 부팅 시 Heap 영역만큼의 메모리를 미리 할당하고 시작하기 때문입니다. 그래서 일반적으로 토스의 서버들은 RSS 메모리 지표가 부팅할 때를 제외하고는 큰 변화가 없습니다.

하지만 이번에 OOM으로 죽은 서버의 residential set size \(RSS\) 메모리 지표를 살펴보면 변화가 있었을 뿐 아니라 꾸준히 우상향 중이었습니다. 여기서부터는 JVM heap 영역이 아닌 native 영역의 메모리를 사용하는 부분을 샅샅이 뒤져 범인을 찾아야 합니다. 하지만 문제가 된 게이트웨이는 JNI나 JNA같이 native 영역의 메모리를 쓰는 곳은 없어서 어디에서 문제가 발생했는지 바로 알기 어려웠습니다. 

한 가지 더 이상한 점은 한 쪽 데이터센터의 게이트웨이만 RSS가 증가한다는 것이었습니다. 토스는 안정적인 서비스 운영을 위해 Active-Active 구조로 이중화 된 데이터센터를 구축하고 있기 때문입니다. 이런 상태에서는 대부분의 트래픽이 양쪽 데이터센터에 1:1의 비율로 인입되는 게 정상입니다.

게이트웨이 접근 로그를 통해 확인해보니, 특정 라우트에 대한 요청은 RSS 지표가 우상향하는 데이터센터로만 인입되고 있었습니다. 그리고 그 라우트에서 다른 라우트에는 없는 필터가 있는걸 확인했습니다. `[CacheRequestBody](https://docs.spring.io/spring-cloud-gateway/reference/spring-cloud-gateway/gatewayfilter-factories/cacherequestbody-factory.html)` 필터였는데요. 캐시로 인한 memory leak. Spring Cloud Gateway에서 기본으로 제공하는 필터지만 이게 범인일 가능성이 크겠다는 생각이 들었습니다. 

그래서 Spring Cloud Gateway Github을 살펴보니 관련된 [수정 사항](https://github.com/spring-cloud/spring-cloud-gateway/pull/2842)을 확인할 수 있었습니다. 요청 바디를 캐싱한 후 이 메모리를 제대로 해제하지 않아 memory leak이 발생한 것이었습니다. 그리고 위 수정은 캐싱된 메모리를 제대로 해제하도록 수정한 내용이었어요. 관련 내용이라는 생각이 들어 그 수정사항이 반영된 버전을 사용해봤더니 native memoery leak이 사라진 것을 확인할 수 있었습니다.

### 2\. WebClient Memory Leak 이슈 파악하기

비슷한 이슈가 서비스에서도 발생을 했는데요. 이 이슈의 문제 원인은 토스 뱅크에서 담당 서버 개발자분과 뱅크 서버 플랫폼팀에서 찾아주셨습니다. 먼저 문제 상황을 설명해 볼게요.

어느 순간부터 토스 뱅크의 특정 서버에서 다음과 같은 로그가 발생하고, 컨테이너 메모리 사용량이 지속적으로 증가하는 것을 발견했습니다.
    
    
    LEAK: ByteBuf.release() was not called before it's garbage-collected

이 로그는 Netty의 `ResourceLeakDetector`에서 찍는 로그인데요. 메시지에서 알 수 있는 것처럼 `ByteBuf`가 GC되기 이전에 `release()`함수가 불리지 않아 memory leak이 발생했습니다. 원인을 찾기 위한 여정은 길었지만, 결론적으로 찾아낸 원인은 Spring WebClient를 생성하는 다음 코드였어요.
    
    
    @Bean
    fun webClient(): WebClient {
        ...
    
        val builder: WebClient.Builder = WebClient.builder()
            ...
            .filter { request, next -> next.exchange(request).cache() }
    
        ...
        return builder.build()
    }

해당 서비스에서는 토스 내부의 다른 마이크로서비스에 접근하기 위해 Spring Framework의 Reactive Stack에서 제공하는 HTTP 클라이언트인 WebClient를 사용하고 있었습니다. 그리고 매 요청마다 connection을 맺는 오버헤드를 줄이기 위해 connection pool을 사용하고 있었는데요. WebClient에서 사용하는 Reactor Netty는 HTTP 요청 후 취소가 발생하면 요청에 사용한 connection을 connection pool에 반납하는 대신 connection을 끊어버리도록 구현되어 있었습니다. 따라서 취소가 많이 발생하면 다른 요청들에서 connection을 새로 맺었고, 이로 인해 성능 저하 문제가 생겼습니다.

WebClient를 사용하는 WebFlux 프로젝트를 사용해 WebClient 요청 취소를 유도하고 실험해보면 아래처럼 connection을 계속 맺는 것을 확인할 수 있습니다.

다시 기존의 Memory Leak 문제로 돌아가 볼게요. WebClient를 생성하는 코드의 `.filter { request, next -> next.exchange(request).cache() }` 구문은 이러한 connection pool 문제를 해결하기 위해 추가된 구문입니다. `[Mono.cache](https://projectreactor.io/docs/core/release/api/reactor/core/publisher/Mono.html#cache--)`를 사용하면 이후의 subscriber에서 cancel 신호가 와도 source mono로 해당 cancel 신호가 전달되지 않습니다. 이 점을 이용해 WebClient 요청에 cancel이 발생해도 Reactor Netty로 전달하지 않고, 결국 conncetion을 끊지 않도록 한 것이죠.

하지만 여기에서 memory leak 문제가 발생했습니다. 앞서의 WebFlux 프로젝트를 사용한 실험과 동일한 환경에서 `.cache`를 이용한 WebClient를 사용하도록 사용하도록 설정하고 다시 실험해보면 아래처럼 connection을 새로 맺지는 않지만 Netty Direct Buffer 사용량이 계속 늘어나는 것을 확인할 수 있습니다.

WebClient는 Reactor Netty를 이용해 HTTP 요청을 한 후 Reactor가 받은 응답 바디를 원하는 객체 형태로 역직렬화화면서 응답 바디에 대한 메모리를 해제합니다. `.cache`를 사용하는 경우에는 WebClient로 cancel 신호가 온 이후에 이러한 로직을 탈 수 없어 memory leak이 발생한 것이죠.

위에서 설명한 WebClient의 `.filter` 구문을 아래처럼 정리했어요. cancel이 발생한 경우 Mono를 정리할 때 응답 바디를 명시적으로 release하도록 수정한 코드입니다.
    
    
    .filter { request, next ->
        val isCancelled = AtomicReference(false)
        val responseRef = AtomicReference<ClientResponse?>(null)
    
        next.exchange(request)
            .doOnNext(responseRef::set)
            .doFinally {
                if (isCancelled.get()) {
                    releaseResponseBody(responseRef.get())
                }
            }
            .cache()
            .doOnCancel {
                isCancelled.set(true)
                releaseResponseBody(responseRef.get())
            }
    }

이렇게 connection pool 이슈와 memory leak 이슈 두가지를 모두 잡을 수 있었습니다.

### 3\. Native Memory Leak의 원인 깊이 이해하기

하지만 왜 heap 영역이 아닌 native memory가 증가하는 걸까요? 원인은 Spring Cloud Gateway와 Spring WebClient가 공통적으로 사용하는 Reactor Netty의 요청∙응답 바디 취급 방식과 관련이 있습니다. Netty가 요청∙응답 바디를 저장하는 데 사용하는 Buffer에는 Direct Buffer와 Heap Buffer가 있는데요. Reactor Netty HttpClient의 기본 설정으로는 소켓 I/O 성능에 이점을 가지는 Direct Buffer를 사용하고 있습니다. JVM heap 영역에 할당되는 Heap Buffer와 다르게 Direct Buffer는 native memory에 직접 할당됩니다. 이러한 특징 때문에 Reactor Netty를 사용하는 프로젝트에서 요청∙응답 바디를 올바르게 처리하지 않으면 heap 영역이 아닌 native 영역에서 memory leak이 발생합니다.

조금 더 구체적으로 살펴볼게요. Reactor Netty는 기본적으로 HTTP 요청∙응답을 담는 데 사용하는 Buffer \(`ByteBuf`\)를 항상 새로 생성하지 않습니다. 대신 Buffer pool을 구성해두고 Buffer가 필요할 때 pool에서 가져다 쓰는 방식을 사용하는데요. Buffer를 사용하고, 사용을 마친 Buffer를 다시 pool로 돌려주는 등의 로직을 구현하는 데 reference counter를 이용합니다. 처음 pool을 통해 Buffer를 할당받을 때 초기 reference counter 값은 1이고, 동일한 Buffer를 다른 곳에서도 사용한다면 `.retain()`함수로 reference counter를 올립니다. 그리고 버퍼의 사용이 끝나면 `.release()`함수로 reference counter를 내려줍니다. 이 때 reference counter 값이 0이 되면 해당 Buffer는 다시 pool로 돌아가게 됩니다. 좀 더 자세한 설명은 [Reference Counted Object](https://netty.io/wiki/reference-counted-objects.html) 문서에서 확인하실 수 있습니다.

정리해볼게요. Spring Cloud Gateway의 memory leak은 요청 바디를 캐싱하기 위해 바디를 가져올 때 reference counter가 올라갔지만, 저장된 바디를 잃어버리면서 reference counter를 다시 내려주는 로직을 타지 못해 발생했어요.

WebClient의 memory leak은 `.cache()` 이후 WebClient 요청이 cancel되어 응답 바디에 대한 메모리 해제가 되지 못해 발생했습니다. 정상적인 경우 `Jackson2JsonDecoder`에서 응답 바디 bytes를 Buffer로부터 읽고 특정 타입의 Java 객체로 변환한 이후 Netty Buffer의 reference counter를 내려주는데 이 로직을 타지 못한거죠.

지금까지 Reactor Netty를 사용하는 프로젝트들에서 발생한 native memory leak 이슈들과 원인을 살펴봤는데요. Reactor Netty 기반의 프로젝트에서는 Direct Buffer를 사용하는 응답∙요청 바디를 다룰 때는 항상 Buffer를 올바르게 소모하거나 잘 해제하는지 꼼꼼하게 확인을 해야 한다는 것을 다시 느낄 수 있었습니다.