# Feign 코드 분석과 서버 성능 개선

**Date:** 2023년 11월 22일
**URL:** https://toss.tech/article/engineering-note-3

---

#### 엔지니어링 노트 3: Feign 코드 분석과 서버 성능 개선

엔지니어링 노트 시리즈는 토스페이먼츠 개발자들이 제품을 개발하면서 겪은 기술적 문제와 해결 방법을 직접 다룹니다. Feign과 다중 스레드를 사용하는 과정에서 생긴 문제를 이해하고 성능 개선까지 한 경험을 공유해요.

얼마 전 토스페이먼츠 서버 모니터링 시스템을 통해 성능 저하 문제를 발견했어요. 약 15,000건 정도의 데이터를 10분 내외로 처리해야 하는 요구사항이 있어 다중 스레드를 활용했는데, 여기서 예상치 못하게 동시성 문제가 생겼습니다. 문제의 핵심은 HTTP 클라이언트 인터페이스인 Feign의 내부 구조에 숨어있었어요. 보통 Feign은 기본 설정을 그대로 사용하기 때문에 여기서 문제가 생길 거라고 예상하지 못했어요. 그래서 이번 문제를 해결하면서 직접 Feign의 내부를 들여다보았습니다. 그 내용과 문제 해결 과정을 공유드릴게요.

#### 💡 문제가 감지된 당시에 사용하던 서버 환경은 Sprinig Boot 2.7.9, 그리고 JDK 11입니다.

### 1단계: 문제 이해하기

당시 문제가 되었던 지점의 로그를 함께 살펴볼게요.
    
    
    [BlockedThread][blocker:http-nio-8080-exec-67][blocked:http-nio-8080-exec-101]
    ...
    
    at java.base@11.0.17/sun.net.www.http.ClientVector.put(KeepAliveCache.java:309) - locked sun.net.www.http.ClientVector@51f75cb3
    at java.base@11.0.17/sun.net.www.http.KeepAliveCache.put(KeepAliveCache.java:172) - locked sun.net.www.http.KeepAliveCache@71a6e252
    at java.base@11.0.17/sun.net.www.protocol.https.HttpsClient.putInKeepAliveCache(HttpsClient.java:663)
    at java.base@11.0.17/sun.net.www.http.HttpClient.finished(HttpClient.java:439)
    at java.base@11.0.17/sun.net.www.http.KeepAliveStream.close(KeepAliveStream.java:99)
    
    

로그 중간에 눈에 들어오는 부분이 있어요. `locked`가 보이네요. 토스페이먼츠 서버 모니터링 시스템은 블로킹 스레드를 탐지했을 때 스택 트레이스에 `locked` 문구를 추가해 줘요. 모니터링 시스템 덕분에 문제가 발생한 지점은 쉽게 찾을 수 있었지만, 원인은 아직 이해하지 못해서 좀 더 자세히 살펴보기로 했습니다.

먼저, 문제가 발생한 `KeepAliveCache` 클래스의 `put` 메서드를 살펴봤어요. 다음 예시 코드에서 볼 수 있듯이 `put` 메서드에는 `synchronized` 키워드가 붙어있어요. 여러 스레드에서 대량으로 API를 호출하고 있는 상황에서 의심이 드는 지점이었죠.
    
    
    // https://github.com/openjdk/jdk/blob/da75f3c4ad5bdf25167a3ed80e51f567ab3dbd01/src/java.base/share/classes/sun/net/www/http/KeepAliveCache.java#L83-L127
    
    /**
      * Register this URL and HttpClient (that supports keep-alive) with the cache
      * @param url  The URL contains info about the host and port
      * @param http The HttpClient to be cached
      */
    public synchronized void put(final URL url, Object obj, HttpClient http){
        // ...
    }

이어서 `put` 메서드를 호출하고 있는 지점이 어디인지 거슬러 올라가 봤어요. `HttpsClient` 클래스의 `kac` 라는 변수가 `put` 메서드를 호출하고 있었어요.
    
    
    // https://github.com/openjdk/jdk/blob/9938b3f62babfc35ee682bd979a6bf08ac7cd348/src/java.base/share/classes/sun/net/www/protocol/https/HttpsClient.java#L670-L683
    
    @Override
    protected void putInKeepAliveCache() {
        // ...
        kac.put(url, sslSocketFactory, this);
    }

마지막으로 `KeepAliveCache kac`이 무엇인지 알아보니 `HttpClient` 클래스의 정적 변수였다는 것을 알게 되었습니다.
    
    
    // https://github.com/openjdk/jdk/blob/da75f3c4ad5bdf25167a3ed80e51f567ab3dbd01/src/java.base/share/classes/sun/net/www/http/HttpClient.java#L96-L97
    
    public class HttpClient extends NetworkClient {
        /* where we cache currently open, persistent connections */
        protected static KeepAliveCache kac = new KeepAliveCache();
    }

이제 실마리가 잡혔어요. `KeepAliveCache kac` 변수에 `static` 키워드가 붙어있기 때문에 `HttpClient` 클래스의 모든 인스턴스가 단 하나의 `KeepAliveCache kac`를 공유해서 사용하게 된 거였어요. `KeepAliveCache kac`는 공유자원인데 여러 스레드가 동시에 `synchronized put` 메서드를 수행하려고 하니 동시성 문제가 발생한 거예요.

정리하자면 Feign 클라이언트를 사용한 API 호출이 엄청나게 많이 발생해서 다중 스레드를 활용했고, 그 과정에서 여러 스레드가 공유자원에 동시에 접근했어요. 결국 필요한 자원이 사용 가능해질 때까지 계속해서 대기 상태에 있었고요. 그래서 서버 성능이 저하되고, 제대로 요청을 받을 수 없는 상태가 되었던 거죠.

### 더 알아보기: Feign 설정

문제 원인은 알았지만 여전히 이해하기 어려운 부분이 있었습니다. 저는 분명히 Feign이 [Apache HttpClient 5](https://hc.apache.org/httpcomponents-client-5.2.x/index.html) 버전을 사용하도록 설정해 뒀거든요. 눈썰미가 좋은 분이라면 눈치채셨을 수 있는데요. 문제가 된 `sun.net.www.http.HttpClient` 클래스는 Feign이 설정하는 기본 HTTP 클라이언트가 아니에요. 그럼 이 클래스는 도대체 어디서 온 걸까요?

Feign의 내부 구현 코드를 따라가 보면 Feign 기본 HTTP 클라이언트는 Java Standard Library의 `HttpURLConnection` 클래스를 사용하는 것을 확인할 수 있어요. 
    
    
    // Client.java: https://github.com/OpenFeign/feign/blob/b0c5db0ddfd24e0515a9143d82353a8d03def32d/core/src/main/java/feign/Client.java#L104-L107
    
    @Override
    public Response execute(Request request, Options options) throws IOException {
        HttpURLConnection connection = convertAndSend(request, options);
        return convertResponse(connection, request);
    }

이 `HttpURLConnection` 클래스가 내부적으로 사용하는 HTTP 클라이언트에서 문제가 되는 `sun.net.www.http.HttpClient`를 사용하고 있어요.
    
    
    // HttpURLConnection.java: https://github.com/JetBrains/jdk8u_jdk/blob/94318f9185757cc33d2b8d527d36be26ac6b7582/src/share/classes/sun/net/www/protocol/http/HttpURLConnection.java#L308
    
    public class HttpURLConnection extends java.net.HttpURLConnection {
        protected HttpClient http;
    }

정리해 볼게요. Feign의 기본 HTTP 클라이언트는 내부적으로 Java Standard Library의 `HttpURLConnection` 클래스를 사용합니다. 자바에서는 이 클래스를 통해 HTTP 커넥션 관련 기능들을 제공하는데요. 이를 구현하는 과정에서 `sun.net.www.http.HttpClient`를 사용하게 되고, 이로 인해 동시성 문제가 발생할 수 있어요. \(참고로 JDK 버전 17 이상에서는 Keep-Alive의 해당 구현을 개선했기 때문에, 더 이상 발생하지 않아요. 아래에서 좀 더 자세히 설명할게요.\)

### 2단계: 문제 해결과 성능 개선

당장 문제를 해소할 수 있는 방법은 두 가지였어요. 첫 번째는 Feign 클라이언트가 사용하는 HTTP 클라이언트의 구현체를 변경하는 것, 두 번째는 JDK 버전을 17 이상으로 업그레이드하는 것이었어요.

1\. Feign Client 구현체 변경 \(Apache HttpClient 5\)

Feign은 Apache HttpClient, OkHttp Client 등 다양한 HTTP 클라이언트를 주입 받아서 동작해요. 이때 특별한 설정을 하지 않으면 Feign이 제공하는 기본 클라이언트를 사용해요. 하지만 앞서 보았듯이, Feign의 기본 클라이언트는 `HttpURLConnection` 클래스를 사용하기 때문에 동시성 문제가 발생할 수 있어요. 즉, `HttpURLConnection` 클래스를 사용하지 않는 HTTP 클라이언트를 사용해야 하죠.

토스페이먼츠에서는 여러 구현체 중 빠르고 효율적인 Apache HttpClient 5를 사용하고 있어요. 다음과 같이 Apache HttpClient 5 의존성을 설정해요.
    
    
    // build.gradle.kts
    dependencies {
        implementation("org.springframework.cloud:spring-cloud-starter-openfeign")
        implementation("io.github.openfeign:feign-hc5")
    }

그런 뒤 Feign이 Apache HttpClient 5를 사용하도록 설정을 변경합니다.
    
    
    // application.yaml
    feign.httpclient.hc5.enabled: true

제가 겪은 문제는 사실 두 번째 Feign 설정을 누락하면서 발생했어요. Apache HttpClient 5 의존성만 주입해 주면 나머지는 언제나처럼 Spring Boot가 마법처럼 해결해 줄 거라 믿은 게 실수였죠. Spring Boot 2.x 버전을 사용하고 계신다면, 꼭 Feign의 위 설정을 `true` 로 바꿔주셔야 해요. 참고로 Spring Boot 3.x 버전부터는 의존성만 주입해도 자동 설정됩니다.

Feign에 HTTP 클라이언트가 주입되는 방식이 궁금하다면, 아래 클래스에서 시작해서 코드를 따라가 보시는 것을 추천할게요. 다음과 같이 `registerFeignClients` 메서드를 따라가다 보면,
    
    
    // FeignClientsRegistrar.java: https://github.com/spring-cloud/spring-cloud-openfeign/blob/eb3a9cb7bc5b9c8b1d03393e5ea34889a5d6e606/spring-cloud-openfeign-core/src/main/java/org/springframework/cloud/openfeign/FeignClientsRegistrar.java#L148-L152
    
    @Override
    public void registerBeanDefinitions(AnnotationMetadata metadata, BeanDefinitionRegistry registry) {
        registerDefaultConfiguration(metadata, registry);
        registerFeignClients(metadata, registry);
    }

`Feign.Builder` static 클래스의 `client` 변수가 적절하게 설정되는 것을 확인할 수 있을 거예요.
    
    
    // Feign.java: https://github.com/OpenFeign/feign/blob/b0c5db0ddfd24e0515a9143d82353a8d03def32d/core/src/main/java/feign/Feign.java#L97
    
    public abstract class Feign {
        public static class Builder extends BaseBuilder<Builder> {
            private 
    
    

특히 Feign이 Apache HttpClient 5 구현체를 사용하도록 설정하는 부분의 클래스 코드는 다음과 같아요. 
    
    
    // FeignAutoConfiguration.java: https://github.com/spring-cloud/spring-cloud-openfeign/blob/cce0de9e898318b7edabab902afda5a45f2ecb41/spring-cloud-openfeign-core/src/main/java/org/springframework/cloud/openfeign/FeignAutoConfiguration.java#L337-L350
    
    @Configuration(proxyBeanMethods = false)
    @ConditionalOnClass(ApacheHttp5Client.class)
    @ConditionalOnMissingBean(org.apache.hc.client5.http.impl.classic.CloseableHttpClient.class)
    @ConditionalOnProperty(value = "feign.httpclient.hc5.enabled", havingValue = "true")
    @Import(org.springframework.cloud.openfeign.clientconfig.HttpClient5FeignConfiguration.class)
    protected static class HttpClient5FeignConfiguration {
        @Bean
    	  @ConditionalOnMissingBean(Client.class)
    	  public Client feignClient(org.apache.hc.client5.http.impl.classic.CloseableHttpClient httpClient5) {
    		    return new ApacheHttp5Client(httpClient5);
        }
    
    }

2\. JDK 버전 17 이상으로 업데이트

JDK 17 버전에서는 위의 디버깅 과정에서 보았던 동시성 문제를 야기하는 내부 구현이 개선되었어요. [코드](https://github.com/openjdk/jdk/blob/dfacda488bfbe2e11e8d607a6d08527710286982/src/java.base/share/classes/sun/net/www/http/KeepAliveCache.java#L89-L139)를 보면 `synchronized` 키워드가 제외된 것을 확인하실 수 있어요. 따라서 위에서 제가 겪은 문제가 발생하지 않아요.

위의 두 가지 해결 방법 중 어느 것을 선택해도 괜찮아요. 아주 간단한 방법이지만 동시성 문제를 해결한 결과,

  * API 처리량이 최소 8배 이상 향상되는 것을 확인할 수 있었어요.
  * 평균 10분 정도 소요되던 작업이 1분 대로 줄었어요.

지금까지 Feign과 다중 스레드를 사용하는 과정에서 생긴 문제에 대해 알아보았어요. 문제 해결과 성능 개선에서 그치지 않고 우리가 의심없이 사용하고 있는 도구 중 하나인 Feign을 깊이 있게 이해할 수 있는 기회였습니다.

👉 이런 문제 해결에 관심이 있다면 [토스페이먼츠 서버 챕터](https://toss.im/career/job-detail?job_id=4071141003&company=%ED%86%A0%EC%8A%A4%ED%8E%98%EC%9D%B4%EB%A8%BC%EC%B8%A0)에 지금 합류하세요\!

Writer 김성두 Edit 한주연