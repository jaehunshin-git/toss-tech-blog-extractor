# NestJS 환경에 맞는 Custom Decorator 만들기

**Date:** 2022년 11월 22일
**URL:** https://toss.tech/article/nestjs-custom-decorator

---

데코레이터는 비즈니스와 상관 없는 로직들을 숨기면서 기능을 변경하거나 확장할 수 있게 합니다. 또한 여러 클래스에서 반복되는 공통 관심사가 있을 때 데코레이터를 사용하면 중복된 코드를 줄이고 코드를 모듈 단위로 관리하는 효과를 거둘 수 있습니다.

이런 이유로 저희 Node.js Chapter에서도 데코레이터를 적극 활용하고 있습니다. 하지만 NestJS에서는 데코레이터를 만들 때 다음과 같은 질문들이 있었습니다.

  1. 데코레이터에서 Provider를 사용해야할 때 어떻게 Provider에 접근할 수 있을까?
  2. 메타데이터를 쓰는 NestJS 데코레이터를 일반 데코레이터와 사용해도 괜찮을까?

NestJS에서 데코레이터를 만들기 위해서는 NestJS의 DI와 메타 프로그래밍 환경 등을 고려해야 합니다. 그래서 이 글을 통해 NestJS에서는 어떻게 데코레이터를 만드는지 살펴보고, 앞의 두 질문들을 고려하여 NestJS 환경에 맞는 데코레이터를 만들어보려고 합니다.

들어가기 전에, 만약 데코레이터나 메타데이터가 생소하시다면 아래 문서들을 읽어보시는 걸 추천드립니다.

  * [Typescript Decorator](https://www.typescriptlang.org/ko/docs/handbook/decorators.html)
  * [reflect-metadata](https://www.npmjs.com/package/reflect-metadata)

    
    
    @Injectable()
    class TestService {
      @Cacheable('key')
      test() {
          // 비즈니스 로직
      }
    }

TestService가 있을 때, 캐싱 로직을 Cacheable 데코레이터를 사용해 비즈니스 로직과 분리하려고 합니다.Cacheable 데코레이터에서 `CacheManager`라는 Provider를 사용하려면 어떻게 접근해야 할까요?
    
    
    @Module{
      imports: [CacheModule.register(...)]
      providers: [TestService]
    }
    class TestModule {}

CacheManager Provider를 export하는 CacheModule을 import 해봅시다.
    
    
    function Cacheable(key: string, ttl: number) {
      return function (target: any, _key: string, descriptor: PropertyDescriptor) {
        const methodRef = descriptor.value;
    
        descriptor.value = async function (...args: any[]) {
        console.log(this) // TestService {}
    
        // TypeError: Cannot read properties of undefined (reading 'get')
        const value = await this.cache.get(key);
        if (value) {
          return value;
        }
    
        const result = await methodRef.call(this, ...args);
        await this.cache.set(key, result, ttl);
        console.log(result)
        return result;
        };
      };
    }

TestModule에서 CacheModule을 import하고 있긴 하지만 TestService에서 CacheManager 를 주입하지 않는 이상 Cacheable에서 CacheManager에 접근할 방법이 없습니다. Cacheable 데코레이터를 사용하려면 클래스에 항상 CacheManager를 주입해주어야 하는 불편함이 있습니다.

게다가 CacheManager를 넣어준다고 해도 멤버 이름을 `cache` 로 강제해야 합니다. 가능한 방법이지만 휴먼 에러가 발생할 수 있어 좋은 방법은 아닙니다.

그렇다면 NestJS 메서드 데코레이터는 어떻게 되어있을까요?

NestJS가 데코레이터를 등록하는 과정은 ‘마킹 - 조회 - 등록’로 크게 세 단계로 나뉩니다. `Cron` 메서드 데코레이터를 예로 들어보겠습니다.

  1. 마킹 - SetMetadata라는 함수로 특정 메서드에 `CRON` 심볼을 메타데이터 키로 등록합니다.
  2. 조회 - 모듈이 초기화되는 시점에 DiscoveryServiced와 MetadataScanner로 모든 Provider 클래스를 순회하며 `CRON` 심볼을 메타데이터로 가지고 있는 메서드들을 찾습니다.
  3. 등록 - 메서드를 찾았으면 해당 메서드를 크론 잡으로 등록합니다.

NestJS에서 제공하는 SetMetadata와 DiscoverService, 그리고 MetadataScanner를 사용하면, 특정 클래스나 메서드만 필터링하여 IoC 내 다른 Provider를 사용해 원하는 로직들을 적용할 수 있습니다.

## SetMetadata

SetMetadata는 타겟\(클래스, 메서드\)에 메타데이터를 마킹하는 데코레이터를 반환하는 함수입니다. NestJS의 코드를 보면 아래와 같습니다. [setMetadata 코드](https://github1s.com/nestjs/nest/blob/HEAD/packages/common/decorators/core/set-metadata.decorator.ts#L22-L37)
    
    
    export const SetMetadata = <K = string, V = any>(
      metadataKey: K,
      metadataValue: V,
    ): CustomDecorator<K> => {
      const decoratorFactory = (target: object, key?: any, descriptor?: any) => {
        // method or class에 메타데이터 등록
        Reflect.defineMetadata(metadataKey, metadataValue, class or method);
        return target;
      };
      decoratorFactory.KEY = metadataKey;
      return decoratorFactory;
    };

`Reflect.defineMetadata(metadataKey, metadataValue, class or method);`

SetMetadata 함수 내부에서는 *`Reflect.defineMetadata` 메서드를 통해 타겟 객체에 metadataKey를 키, metadataValue를 값으로 하는 [내부 슬롯](https://medium.com/jspoint/what-are-internal-slots-and-internal-methods-in-javascript-f2f0f6b38de)을 정의합니다. \(`[[Metadata]]` \)*`Reflect` 는 [reflect-metadata](https://www.npmjs.com/package/reflect-metadata) 라이브러리가 설치되어있는 경우 사용할 수 있습니다. 메타데이터를 정의하거나 조회하는 데 사용합니다.

`SetMetadata(KEY, value) -> CustomDecorator;`

SetMetadata의 리턴값은 클래스, 메서드 데코레이터로 사용 가능합니다. 해당 데코레이터로 타겟 클래스나 메서드에 대한 메타데이터를 설정할 수 있습니다.
    
    
    const SOMETHING = Symbol('SOMETHING')
    
    function CustomDecorator(key: string | symbol) {
      // SetMetadata(SOMETHING, key)와 다른 데코레이터를 합성할 수 있습니다.
      return applyDecorators(SetMetadata(SOMETHING, key), AnotherDecorator)
    }
    
    @CustomDecorator('KEY1')
    class DecoratedClass {}

`DecoratedClass`에 `SOMETHING` 심볼을 메타데이터 키, `'KEY1'`을 메타데이터 값으로 등록합니다.

## DiscoveryService

NestJS는 DiscoveryModule 을 제공합니다. DiscoveryModule의 DiscoveryService에서는 내부적으로 modulesContainer를 사용하여 모든 모듈의 Controller와 Provider 클래스를 조회할 수 있습니다.

`DiscoverService`를 사용하여 모든 Provider 클래스를 순회하며, SetMetadata로 등록했던 메타데이터 키로 특정 Provider를 필터링할 수 있게 됩니다.

[DiscoveryService 코드](https://github.com/nestjs/nest/blob/master/packages/core/discovery/discovery-service.ts)
    
    
    @Injectable()
    export class DiscoveryService {
      constructor(private readonly modulesContainer: ModulesContainer) {}
    
      getProviders(
        options: DiscoveryOptions = {},
        modules: Module[] = this.getModules(options),
      ): InstanceWrapper[] {
        return modules.flatMap(item => [...item.providers.values()]);
      }
    
      // ...생략
    }

CustomDecorator 가 붙은 메서드를 찾는 과정을 예로 들어보겠습니다. 메타데이터 키는 `CUSTOM_DECORATOR` 심볼이고, 메타데이터 값은 `test-value `입니다.
    
    
    export const CUSTOM_DECORATOR = Symbol("CUSTOM_DECORATOR");
    export const CustomDecorator = SetMetadata(CUSTOM_DECORATOR, 'test-value');
    
    @CustomDecorator
    @Injectable()
    class TestService {
      test() {}
    }

아래의 `explorerService.find(CUSTOM_DECORATOR)` 메서드를 실행하면 어떻게 될까요?
    
    
    import { Injectable } from '@nestjs/common';
    import { DiscoveryService, MetadataScanner, Reflector } from '@nestjs/core';
    
    @Injectable()
    export class ExplorerService {
      constructor(
        private readonly discoveryService: DiscoveryService,
      ) {}
    
      find(metadataKey: string | symbol) {
        const providers = this.discoveryService.getProviders();
    
        return providers
          .filter((wrapper) => wrapper.isDependencyTreeStatic())
          .filter(({ metatype, instance }) => {
            if (!instance || !metatype) {
              return false;
            }
            return Reflect.getMetadata(metadataKey, metatype);
          })
          .map(({ instance }) => instance);
      }
    }

첫번째 필터: `filter((wrapper) => wrapper.isDependencyTreeStatic())`

request scope가 아닌 싱글톤 프로바이더만 필터링합니다.

두번째 필터: `Reflect.getMetadata(metadataKey, metatype)`

해당 필터는 메타데이터가 등록된 클래스만 필터링합니다.

`metatype` 은 `class TestService` 와 같이 해당 Provider의 클래스를 의미합니다.

`Reflect.getMetadata(metadataKey, metatype)` 은 metatype\(클래스\)에 `metadataKey`로 등록된 메타데이터의 값을 가져옵니다. TestService 클래스의 경우 메타데이터 키는 `CUSTOM_DECORATOR` 이고 값은 `test-value` 입니다.

만약 등록된 메타데이터가 없으면 undefined를 반환하고 해당 Provider는 필터링됩니다.

## MetadataScanner

앞의 DiscoverService의 예시에서는 데코레이팅된 메서드를 가진 인스턴스에 접근하는 데 그쳤습니다. 실제 데코레이팅된 메서드에 접근하기 위해서는 DiscoveryModule에서 제공하는 `MetadataScanner` 를 사용해야 합니다.

[MetadataScanner 코드](https://github1s.com/nestjs/nest/blob/HEAD/packages/core/metadata-scanner.ts#L9-L40)
    
    
    export class MetadataScanner {
      public scanFromPrototype<T extends Injectable, R = any>(
        instance: T,
        prototype: object,
        callback: (name: string) => R,
      ): R[] {
        const methodNames = new Set(this.getAllFilteredMethodNames(prototype));
        return iterate(methodNames)
          .map(callback)
          .filter(metadata => !isNil(metadata))
          .toArray();
      }
    
      *getAllFilteredMethodNames(prototype: object): IterableIterator<string> {
        // prototype에 등록된 method 이름들을 가져온다.
    
    

`scanFromPrototype` 는 `getAllFilteredMethodNames` 메서드로 인스턴스의 모든 메서드 이름들을 가져와 인자로 받은 callback을 실행시킵니다. 이 중에서 메타데이터가 있는 메서드만 필터링합니다.

`scanFromPrototype` 의 callback 파라미터에서 인스턴스 메서드에 접근할 수 있습니다. 이제 메서드에 접근해 데코레이팅 함수로 덮어씌울 수 있습니다.

`SetMetadata`, `DiscoveryService`, `MetadataScanner` 모든 재료들이 모였으니 Provider에 접근 가능한 메서드 데코레이터를 만들어봅시다.

Cacheable 데코레이터

메서드에 `CACHEABLE` 심볼을 메타데이터 키로, ttl을 메타데이터 값으로 설정합니다.
    
    
    export const CACHEABLE = Symbol('CACHEABLE');
    export const Cacheable = (ttl: number) => SetMetadata(CACHEABLE, ttl);
    
    @Injectable()
    class TargetClass {
      @Cacheable(0)
      test() {}
    }

CacheDecoratorRegister 클래스
    
    
    @Injectable()
    export class CacheDecoratorRegister implements OnModuleInit {
      constructor(
        private readonlydiscoveryService: DiscoveryService,
        private readonly metadataScanner: MetadataScanner,
        private readonly reflector: Reflector,
        private readonly cache: Cache,
      ) {}
    
      onModuleInit() {
        return this.discoveryService
          .getProviders() // #1. 모든 provider 조회
          .filter((wrapper) => wrapper.isDependencyTreeStatic())
          .filter(({ instance }) => instance && Object.getPrototypeOf(instance))
          .forEach(({ instance }) => {
            this.metadataScanner.scanFromPrototype(
              instance,
              Object.getPrototypeOf(instance),
              (methodName) => {
    	    // #2. 메타데이터 value
                const ttl = this.reflector.get(CACHEABLE, instance[methodName]);
                if (!ttl) {
                  return;
                }
    
                const methodRef = instance[methodName];
    
                // #3. 기존 함수 데코레이팅
                instance[methodName] = async function (...args: any[]) {
                  const name = `${instance.constructor.name}.${methodName}`;
                  const value = await this.cache.get(name, args);
                  if (value) {
                    return value;
                  }
    
                  const result = await methodRef.call(instance, ...args);
                  await this.cache.set(name, args, result, ttl);
                  return result;
                };
              },
            );
          });
      }
    }

해당 클래스를 모듈의 provider에 등록하면, onModuleInit 단계에서 `@Cacheable`로 데코레이팅된 메서드를 찾아 기존 메서드를 덮어씌웁니다.

메서드 데코레이터를 만드는 과정은 다음과 같습니다.

\#1. 모든 Provider 클래스를 순회하며

\#2. 특정 메타데이터가 등록된 메서드를 찾아

\#3. 기존 메서드를 덮어씌웁니다.

\#3의 과정에서, `CacheDecoratorRegister` 생성자에 주입한 CacheManager를 사용할 수 있습니다.

그런데 메서드 데코레이터를 만들 때마다 매번 이렇게 복잡한 과정을 거쳐야하는 걸까요? 저희 챕터에서는 메서드 데코레이터마다 반복되는 과정을 AopModule이라는 모듈로 해결했습니다.

해당 모듈은 2022년 12월에 오픈소스로 공개되었습니다. 현재 npm에서 [@toss/nestjs-aop](https://www.npmjs.com/package/@toss/nestjs-aop) 라이브러리를 다운 받아 사용해보실 수 있습니다.

관련해서 [NestJS 밋업에서 발표한 자료](https://www.youtube.com/watch?v=VH1GTGIMHQw&t=3000s)도 있으니 함께 참고하시면 좋을 듯 합니다. :\)

## AopModule

AopModule이 데코레이터들을 등록하는 과정은 이렇습니다.

간단히 설명하면

  1. Aspect 데코레이터가 붙은 클래스를 찾고 \(CacheableDecorator\)
  2. Cacheable 데코레이터가 붙은 함수를 찾아 \(FooService.foo\)
  3. 1번 클래스의 wrap 함수로 2번의 함수를 감쌉니다. \(CacheableDecorator.wrap\)

코드를 보며 좀 더 자세히 설명해볼게요.

### 1\. Aspect 데코레이터 사용

Aspect 데코레이터
    
    
    import { applyDecorators, Injectable } from '@nestjs/common';
    
    export const ASPECT = Symbol('ASPECT_CLASS');
    
    export function Aspect() {
      return applyDecorators(SetMetadata(ASPECT, 'ASPECT_CLASS'), Injectable);
    }

데코레이터 사용
    
    
    @Aspect()
    export class CacheLazyDecorator {}

데코레이터 로직을 실행할 클래스에 `ASPECT` 라는 심볼을 메타데이터로 설정합니다.

### 2\. 데코레이터 생성
    
    
    export const CACHEABLE = Symbol('CACHEABLE');
    export const Cacheable = (ttl: number) => SetMetadata(CACHEABLE, ttl);
    
    
    class FooService {
    	@Cacheable(1000)
    	foo() {}
    }

특정 심볼\(또는 문자열\)을 메타데이터 키로 하여 SetMetadata로 원하는 데코레이터를 만듭니다.

### 3\. LazyDecorator 구현

AopModule에 등록되는 모든 데코레이터들은 LazyDecorator 인터페이스를 구현해야 합니다. 데코레이팅 하는 시점을 모듈이 초기화되는 시점으로 미루기 때문에 LazyDecorator라고 합니다.

LazyDecorator 인터페이스
    
    
    export interface LazyDecorator {
      wrap(reflector: Reflector, instance: any, methodName: string): Decorator | undefined;
    }

CacheLazyDecorator 구현
    
    
    @Aspect()
    export class CacheLazyDecorator implements LazyDecorator {
      constructor(@Inject(CACHE_MANAGER) private readonly cache: CacheManager){}
    
      wrap(reflector: Reflector, instance: any, methodName: string) {
        const ttl = reflector.get(CACHEABLE, instance[methodName]);
        if (!ttl) {
          return;
        }
    
        const methodRef = instance[methodName];
        const name = `${instance.constructor.name}.${methodName}`;
        return async (...args: any[]) => {
          const value = await this.cache.get(name);
          if (value) {
            return value;
          }
    
          const result = await methodRef.call(instance, ...args);
          this.cache.set(name, result, ttl);
          return result;
        };
      }
    }

접근하고자 하는 Provider는 이제 생성자에 주입하여 사용할 수 있습니다.

### 4\. AutoAspectExecutor

onModuleInit 단계에서 AopModule의 AutoAspectExecutor 가 ASPECT가 붙은 데코레이터 클래스들의 wrap 함수를 실행시키며 기존 메서드를 덮어씌웁니다.

AutoAspectExecutor 코드
    
    
    @Injectable()
    export class AutoAspectExecutor implements OnModuleInit {
      constructor(
        private readonlydiscoveryService: DiscoveryService,
        private readonly metadataScanner: MetadataScanner,
        private readonly reflector: Reflector,
      ) {}
    
      onModuleInit() {
        const providers = this.discoveryService.getProviders();
        const lazyDecorators = this.lookupLazyDecorators(providers);
        if (lazyDecorators.length === 0) {
          return;
        }
    
        providers
          .filter((wrapper) => wrapper.isDependencyTreeStatic())
          .filter(({ instance }) => instance && Object.getPrototypeOf(instance))
          .forEach(({ instance }) => {
            this.metadataScanner.scanFromPrototype(
              instance,
              Object.getPrototypeOf(instance),
              (methodName) =>
                lazyDecorators.forEach((lazyDecorator) => {
                  const wrappedMethod = lazyDecorator.wrap(this.reflector, instance, methodName);
                  if (wrappedMethod) {
                    instance[methodName] = wrappedMethod;
                  }
                }),
            );
          });
      }
    
      private lookupLazyDecorators(providers: any[]): LazyDecorator[] {
        // this.reflector.get(ASPECT, metatype) 결과값이 존재하는 providers만 필터링
      }
    }

Provider에 접근 가능한 데코레이터를 만드는 과정을 다시 요약하면 이렇습니다.

  1. `SetMetadata`로 필터링할 클래스에 메타데이터를 등록하고
  2. `DiscoveryService`로 모든 Provider를 조회하며
  3. 등록된 Metadata로 특정 클래스나 메서드를 필터링하여 원하는 작업을 하면 됩니다.

Provider에 접근이 필요없는 경우 일반 메서드 데코레이터를 구현하면 될 것입니다. 하지만 메타데이터를 사용하는 NestJS 데코레이터를 일반 데코레이터와 함께 사용해도 괜찮을까요?

결론부터 말하자면 둘을 함께 사용하면 예상치 못한 버그가 발생할 수 있습니다.

### 일반 메서드 데코레이터를 사용하면 안되는 이유

메타데이터를 등록하는 다른 데코레이터와 함께 쓰이는 경우, 기존 메서드가 덮어씌워지면서 프로토타입에 등록된 메타데이터가 사라질 수 있습니다.
    
    
    export function OnError(handler: (e: Error) => void) {
      return (target: object, key?: any, descriptor?: any) => {
        const originMethod = descriptor.value;
        descriptor.value = (...args: any[]) => {
          try {
            return originMethod.call(this, ...args);
          } catch (error) {
            handler(error);
          }
        };
      };
    }

OnError 데코레이터는 기존 메서드를 새로운 메서드로 덮어씌웁니다.

아래 코드에서는 메타데이터를 등록하는 RegisterMetadata 데코레이터와 OnError 데코레이터를 함께 사용하고 있습니다. 데코레이터 선언 순서에 따라 기존에 등록된 메타데이터는 사라질 수 있습니다.

아래 메서드 중에 `Reflect.getMetadata`를 했을 때 메타데이터가 사라지는 메서드는 무엇일까요?
    
    
    @Injectable()
    class TestService {
      @OnError(console.log)
      @RegisterMetadata('value')
      test() {
        throw new Error('error');
      }
    
      @RegisterMetadata('value2')
      @OnError(console.log)
      test2() {
        throw new Error('error');
      }
    }

정답은 test 메서드입니다. 실행 결과는 [타입스크립트 플레이그라운드](https://www.typescriptlang.org/play?noImplicitAny=false&noImplicitThis=false&ssl=54&ssc=89&pln=51&pc=1#code/PTAEEsFsAcHsCcAuoDk8CmAzANugxogLSTqICGAJmeSgFC16wB2AzsgMqkCypl1ZoALygAPAGkhoNvHBMA5gBpQANUlkmATwB8AClqhQJclXJj0GgFygxC-Yd4myystgCu6K8tsBKIVtAA3naMrLC4AHTYsHI6KJyIPMb8oICTy4AANSjewcxsoBT4CNQIAGJkBAgakjrk8HKkVrAARgBW+IhKANbmAPxW6hpK+Sx4MtCICL2g-b6C-kEGBuCYoDpDI+BjCL7zCwYhLGHokdGxgCpdgAMLgA7NgC7jgAyLoICPLYC6HShKRnzkzm7oWbsGAEpYXAEcL5TCydCJD5kHTvRxmAb2JKfFzuQboYajcbwcIAN1RPwA3HZdhhEK54Ew8hj1pt4MTdgBfOyMhnUxjwIrwUrleAacJiACiAE1JHD+Ai2WSKVT8hyuTzsRpiaz6JhXEwCOBmKAAPJMQXweAIHQAC3UFFw8CsOg8oENxvgM38uNg4Ao22yoQiURiACJ9Q6EKk0n7vFLSDKVjU6ogGi02p0en1NOjMRtsZNpn5AiTQPtDsd-YGjcHACdDgEjVqyAC1XABhDoEAds2AFtHAA8jgAY6sNsvY5ZAIcByWSJU2wCiSNZYhB4gld6npulT75VcLLsi1FgpjQAbQAus7c39QIg+fuD6BpZTQH2B0whyPwngXNhqqbwCwlMvwqu5Cxw3mDIz82oPBTRWdBS2tKZNE9U9QHNJhLTA21wN-A9mSZNlVWZBge1Af5BQAcQASXYAAVQV-gAfS4QUSIAQQAEVoujJHYDRIEaMJYjwojSPIqiaIYpjaMybDWGQQEBzYMCoUcKp8W+KxpFkOQ93iGT+B0bjiLIyjqLoxi6KUeT3CyBhsDIFgWFAEiMUQTh4FxcA8HQE8AAES0dHQCx9aJflAVyJNfRBpIcDSUGM9ARIMYK2B0aCFkQU1jQAd1AJh0FSoN4FiMDHUyDD6AMAL0Ek4L4HU8hYgigAmKL-I8k1vKOX0-JixBqrik9oqS2BUvSzLwJy8D8pZWgsP2ZA2vsxznMkfrrNs6anPQOL6CaotYjapFoVeXCgTacJYwqmEtN43SBIM2ilCmsCZqONrvCydbfU22zqu2xxdsBHADqO0LKtOnT+P0oTrsW27lvCNrqseoA)[에서](https://www.typescriptlang.org/play?noImplicitAny=false&noImplicitThis=false&ssl=54&ssc=89&pln=51&pc=1#code/PTAEEsFsAcHsCcAuoDk8CmAzANugxogLSTqICGAJmeSgFC16wB2AzsgMqkCypl1ZoALygAPAGkhoNvHBMA5gBpQANUlkmATwB8AClqhQJclXJj0GgFygxC-Yd4myystgCu6K8tsBKIVtAA3naMrLC4AHTYsHI6KJyIPMb8oICTy4AANSjewcxsoBT4CNQIAGJkBAgakjrk8HKkVrAARgBW+IhKANbmAPxW6hpK+Sx4MtCICL2g-b6C-kEGBuCYoDpDI+BjCL7zCwYhLGHokdGxgCpdgAMLgA7NgC7jgAyLoICPLYC6HShKRnzkzm7oWbsGAEpYXAEcL5TCydCJD5kHTvRxmAb2JKfFzuQboYajcbwcIAN1RPwA3HZdhhEK54Ew8hj1pt4MTdgBfOyMhnUxjwIrwUrleAacJiACiAE1JHD+Ai2WSKVT8hyuTzsRpiaz6JhXEwCOBmKAAPJMQXweAIHQAC3UFFw8CsOg8oENxvgM38uNg4Ao22yoQiURiACJ9Q6EKk0n7vFLSDKVjU6ogGi02p0en1NOjMRtsZNpn5AiTQPtDsd-YGjcHACdDgEjVqyAC1XABhDoEAds2AFtHAA8jgAY6sNsvY5ZAIcByWSJU2wCiSNZYhB4gld6npulT75VcLLsi1FgpjQAbQAus7c39QIg+fuD6BpZTQH2B0whyPwngXNhqqbwCwlMvwqu5Cxw3mDIz82oPBTRWdBS2tKZNE9U9QHNJhLTA21wN-A9mSZNlVWZBge1Af5BQAcQASXYAAVQV-gAfS4QUSIAQQAEVoujJHYDRIEaMJYjwojSPIqiaIYpjaMybDWGQQEBzYMCoUcKp8W+KxpFkOQ93iGT+B0bjiLIyjqLoxi6KUeT3CyBhsDIFgWFAEiMUQTh4FxcA8HQE8AAES0dHQCx9aJflAVyJNfRBpIcDSUGM9ARIMYK2B0aCFkQU1jQAd1AJh0FSoN4FiMDHUyDD6AMAL0Ek4L4HU8hYgigAmKL-I8k1vKOX0-JixBqrik9oqS2BUvSzLwJy8D8pZWgsP2ZA2vsxznMkfrrNs6anPQOL6CaotYjapFoVeXCgTacJYwqmEtN43SBIM2ilCmsCZqONrvCydbfU22zqu2xxdsBHADqO0LKtOnT+P0oTrsW27lvCNrqseoA) 직접 확인하실 수 있습니다.
    
    
    const testService = new TestService()
    
    // undefined
    console.log('test metadata', Reflect.getMetadata(REGISTER_METADATA, testService.test))
    // value2
    console.log('test2 metadata', Reflect.getMetadata(REGISTER_METADATA, testService.test2))

왜 이렇게 되는 걸까요? 데코레이터의 실행 순서가 힌트입니다.

g∘f\(x\) = g\(f\(x\)\) 와 같은 합성 함수가 있을 때 선언은 g가 f보다 먼저 되었지만 실행은 f 함수가 먼저 실행됩니다. 마찬가지로 데코레이터는 평가될 때는 선언된 순서대로 위에서 아래로, 실행될 때는 아래에서 위로 실행됩니다.

RegisterMetadata에서 `Reflector.defineMetadata`가 먼저 실행되고 그 다음 OnError 데코레이터가 기존 함수를 덮어씌웁니다.

덮어씌워지면서 기존에 메타데이터가 저장된 프로토타입과 끊기게 되고 `test` 메서드에서 메타데이터를 찾을 수 없게 됩니다.

이런 사례도 있을 수 있습니다.
    
    
    @Injectable()
    class TossScheduler {
    
      @OnError(console.log)
      @Cron('*/10 * * * *')
      task() {
        // do something
      }
    }

`@nestjs/schedule` 의 Cron 데코레이터 역시 CRON 심볼을 메타데이터로 등록합니다. 모듈이 초기화되는 시점에 해당 메타데이터가 등록된 메서드들을 조회하여 cron job을 등록합니다.

하지만 OnError 데코레이터가 Cron 데코레이터 이후에 실행됨으로써 메타데이터가 사라지게 되고, NestJS에서는 task 메서드를 찾지 못해 cron job을 등록하지 못하게 됩니다.

이렇듯 일반 메서드 데코레이터를 NestJS 환경에서 그냥 사용하게 되면 개발자의 실수에 의해 코드의 동작이 바뀔 수 있습니다. 데코레이터 실행 순서나 메타데이터 환경에 대해 알고 있지 못하다면 이런 류의 버그를 찾는 데는 시간이 오래 걸릴 지도 모릅니다.

이를 방지하기 위해서는 메타데이터를 고려하여 데코레이터를 생성해야 합니다.

## 메타데이터를 유지하는 데코레이터

메타데이터를 유지하는 가장 naive한 방법은, 오버라이딩 되기 전에 메타데이터를 저장해둔 뒤 오버라이딩이 끝나면 메타데이터를 다시 등록해주는 것입니다.

OnErrorPreserveMeta 코드
    
    
    export function OnErrorPreserveMeta(handler: (e: Error) => void) {
      return (target: object, key?: any, descriptor?: any) => {
        const originMethod = descriptor.value;
    
        //  오버라이딩 되기 전의 메타데이터를 저장해놨다가
        const metaKeys = Reflect.getOwnMetadataKeys(descriptor.value);
        const metas = metaKeys.map((k) => [
          k,
          Reflect.getMetadata(k, descriptor.value),
        ]);
    
        descriptor.value = (...args: any[]) => {
          try {
            return originMethod.call(this, ...args);
          } catch (error) {
            handler(error);
          }
        };
    
        // 오버라이딩 된 메서드에 대해 메타데이터 재등록
        metas.forEach(([k, v]) => Reflect.defineMetadata(k, v, descriptor.value));
      };
    }

직관적이지만 매번 Decorator를 만들어줄 때마다 이런 과정을 거쳐야 하는 게 불편합니다. 이를 해결하는 좀 더 간단한 방법이 있습니다.

## 프로토타입을 사용해 메타데이터 유지하기

SetMetadata 파트에서 Reflect.defineMetadata 는 타겟 객체에 \[\[Metadata\]\] 라는 내부 슬롯을 정의한다고 말씀드렸습니다.

내부 슬롯 또한 프로토타입의 내부 프로퍼티이니, 기존 프로토타입에 메타데이터 내부 슬롯이 저장되어있을 것입니다. 따라서 새롭게 정의한 메서드에 기존 프로토타입을 연결해주면 됩니다.

변경된 OnErrorPreserveMeta 코드
    
    
    export function OnErrorPreserveMeta(handler: (e: Error) => void) {
      return (target: object, key?: any, descriptor?: any) => {
        const originMethod = descriptor.value;
    
        const wrapper = (...args: any[]) => {
          try {
            return originMethod.call(this, ...args);
          } catch (error) {
            handler(error);
          }
        };
    
        Object.setPrototypeOf(wrapper, originMethod); // 이 줄만 추가
        descriptor.value = wrapper;
      };
    }

`Object.setPrototypeOf(arg1, arg2)` 은 arg1 객체의 프로토타입을 arg2로 설정합니다.

기존 메서드를 덮어씌운 후 `Object.setPrototypeOf(wrapper, originMethod)`로 originMethod를 wrapper의 프로토타입으로 설정해주면 메타데이터가 유지됩니다.
    
    
    @Injectable()
    class TestService {
      @OnError(console.log)
      @RegisterMetadata('value')
      test() {
        throw new Error('error');
      }
    }
    
    const testService = new TestService()
    
    console.log('test metadata', Reflect.getMetadata(REGISTER_METADATA, testService.test)) // 'value'

메타데이터와 NestJS의 `DiscoveryModule` 을 사용하여 NestJS의 IoC 컨테이너에 접근할 수 있는 데코레이터, 그리고 메타데이터를 유지할 수 있는 데코레이터를 만들어보았습니다.

메타데이터 태깅, DiscoveryModule, 프로토타입을 사용해 NestJS 환경에 맞는 데코레이터를 만들 수 있었습니다. 이 글을 통해 더욱 더 NestJS의 Aop 패턴에 맞는 프로그래밍을 하게 되었기를 바랍니다.

또한 토스 Node.js 챕터는 토스의 다양한 제품과 라이브러리 개발을 위해 팀원들의 지속적인 성장이 중요하다고 믿으며, 이를 위해 코드 리뷰, 스터디와 엔지니어링 세미나 등을 통해 꾸준히 공부하고 공유하는 자리를 가지고 있으니 많은 관심 부탁드립니다.

## References

  * <https://zuminternet.github.io/nestjs-custom-decorator/>
  * <https://github.com/nestjs/nest>
  * <https://github.com/nestjs/swagger/issues/217>
  * <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Object/setPrototypeOf>