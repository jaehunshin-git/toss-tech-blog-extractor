# React Native에서 타입 안전한 파일 기반 라우팅 구현하기

**Date:** 2025년 3월 26일
**URL:** https://toss.tech/article/rn-toss-bedrock

---

안녕하세요. React Native Framework Team에 속한 Frontend Platform Engineer 강선규입니다. 오늘 소개해 드릴 이야기는 토스에서 만드는 React Native Framework와 그 기능에 관한 이야기에요.

## Granite이란?

토스는 이전 글 [토스가 꿈꾸는 React Native 기술의 미래](https://toss.tech/article/react-native-2024)에서 자체적인 React Native 프레임워크를 개발한다고 공개했어요. 이 글을 통해서 해당 프레임워크, Granite을 처음 공개해요.

Granite은 React Native 프레임워크로, 단단한 화강암을 의미하는 이름처럼 프로젝트 개발에 견고한 기초를 제공해요. Granite은 안정적이고 신뢰할 수 있는 구조를 바탕으로, 다양한 플랫폼에서 일관된 성능과 사용자 경험을 제공해요. 아직은 토스 내부 및 일부 협력사만 사용할 수 있지만, 추후에 공개를 목표로 오픈소스를 목표로 하고 있어요. \(5월 29일자로 Granite는 외부 공개 되었어요🎉 <https://github.com/toss/granite>\)

기존 React Native 생태계에는 이미 `Expo` 같은 프레임워크가 존재하며, `expo-router`는 파일 기반 라우팅\(File-Based Routing\)을 사용해 화면을 정의합니다. Granite 역시 이와 유사하게 파일 기반 라우팅을 채택했으며, 이는 `react-navigation` v6를 기반으로 합니다. 

오늘은 토스 자체 React Native 프레임워크 Granite이 어떻게 파일 기반 라우팅의 문제를 해결했는지 소개해드릴게요.

## 기존 파일 기반 라우팅의 문제점

기존의 Granite 파일 기반 라우팅은 `React Navigation`을 추상화한 형태로, `pages` 폴더에 컴포넌트를 만들고 `export default`로 화면을 자동 등록하는 방식이었어요.

예제 코드:
    
    
    export default function Page() {
        const params = useRoute().params;
     
        return <View>Hello {params.name}</View>;
    }

하지만 이 방식은 화면 간 이동할 때 필요한 파라미터의 타입을 정의하기 어렵다는 문제가 있었어요. 그 결과, 어떤 파라미터가 필요한지 명확하게 알기 힘들었어요.

## 1\. Type-Safe Routing을 향한 발전

이런 문제 때문에 최근 웹 프론트엔드에서는 `tanstack router`처럼 타입 안정성\(Type-Safety\)을 핵심으로 하는 라우터 프레임워크가 인기를 끌고 있어요.

Granite도 기존 방식의 한계를 보완하기 위해 tanstack router의 방식에서 영감을 받아 Type-Safe한 파일 기반 라우팅을 도입했어요.

이 방식은 co-location 원칙을 적용해서 각 화면의 타입을 같은 위치에서 정의하도록 했어요. 덕분에 더 명확한 개발 경험을 제공할 수 있어요.

### 개선된 방식 예시
    
    
    import React from 'react';
    import { View, Text } from 'react-native';
    import { createRoute } from '@granite-js/react-native';
    import { z } from 'zod';
    
    // 라우트 정의
    export const Route = createRoute('/page-a', {
      component: Page,
      validateParams: (params) => 
        z.object({ name: z.string() }).parse(params), // 파라미터 검증 및 타입 추론
    });
    
    // 화면 컴포넌트
    function Page() {
      const params = Route.useParams(); // { name: string }으로 자동 추론됨
      return (
        <View>
          <Text>Hello, {params.name}!</Text>
        </View>
      );
    }

이 방식에서는 `validateParams`로 파라미터를 검증하고, 그 결과를 자동으로 추론해서 `params` 타입으로 활용할 수 있어요. 그래서 라우팅이 더 명확하고 안전해졌어요.

기존에는 `export default`를 기준으로 페이지가 등록됐지만, 이제는 `export Route`의 `component` 속성을 기준으로 페이지가 등록돼요.

또한, `validateParams`를 활용해 각 화면의 타입을 명확하게 정의할 수 있도록 개선됐어요.

### 🚩 useParams 내부 구현

화면의 파라미터는 일반적으로 react-navigation의 `useRoute().params` 를 통해 가져올 수 있어요.

Granite에서는 이를 활용하여 라우팅 로직과 독립적인`useParams`를 별도로 정의하고, 해당 훅을 createRoute에 연결하는 방식을 사용했어요.

실제 구현은 복잡할 수 있지만, 이해를 돕기 위해 간소화된 코드로 설명할게요.

✅ 1. 독립적인 useParams 구현하기
    
    
    import { useRoute } from "@react-navigation/native";
    
    function useParams() {
      return useRoute().params;
    }

이렇게 만든 `useParams`는 현재 활성화된 라우트의 파라미터만 가져오며, 아직 타입 안정성은 없어요.

✅ 2. createRoute에 useParams를 연결하기

이제 위에서 만든 `useParams`를 createRoute의 반환값에 넣고, `validateParams`를 통해 타입 추론을 추가했어요.
    
    
    export interface RouteOptions<T extendsReadonly<object | undefined>> {
      validateParams?: (params: Readonly<object | undefined>) => T;
      component: React.FC<any>;
    }
    
    export const createRoute = <T extends Readonly<object | undefined>>(
      path: keyof RegisterScreen,
      options: RouteOptions<T>
    ) => {
      const { component, ...restOptions } = options;
    
      return {
        useParams: () => useParams() as T, // validateParams를 통해 타입이 추론됨
      };
    };

위 코드에서 `useParams`가 호출될 때, `validateParams`의 반환 타입\(T\)을 통해 파라미터의 타입이 명확히 추론돼요.

## 2\. 화면 타입의 중앙 관리

앞서 설명한 것처럼, `Route.useParams()`는 각 화면에서 정의한 `validateParams`를 기반으로 파라미터의 타입을 자동 추론해서 제공합니다.

이렇게 추론된 각 화면의 타입은 외부 파일에서 중앙 집중적으로 관리하고 있어요. 이를 위해 타입 선언 병합\(Declaration Merging\)을 사용해서, 라이브러리 내부에서도 각 화면의 타입 정보를 명확히 알 수 있게 했어요.

다음 예시를 살펴볼게요:
    
    
    import { Route as _PageARoute } from '../pages/page-a';
    import { Route as _PageBRoute } from '../pages/page-b';
    
    // @granite-js/react-native 라이브러리에 선언 병합
    // 화면 경로가 키가 되고, 화면 파라미터 타입이 값이 돼요.
    declare module '@granite-js/react-native' {
      interface RegisterScreen {
        '/page-a': ReturnType<typeof _PageARoute.useParams>;
        '/page-b': ReturnType<typeof _PageBRoute.useParams>;
      }
    }

이 코드가 의미하는 것:

  * 화면 경로\(예: /page-a, /page-b\)가 타입 등록의 키\(Key\)가 돼요.
  * 각 경로에 해당하는 값\(Value\)은 Route.useParams\(\)의 반환값으로, 각 페이지에서 정의한 validateParams의 결과 타입이에요.
  * 새로운 페이지를 추가할 때마다 여기에 화면의 경로와 타입을 간단히 추가하면, 전체 앱의 라우팅 타입을 명확하게 관리할 수 있어요.

이렇게 하면 모든 페이지에 관해서 모든 타입을 한번에 관리할 수 있어요.

## 3\. 컴파일 타임 자동 타입 생성

화면이 많아질수록 수동으로 모든 타입을 관리하는 건 어렵기 때문에, 이를 자동화하는 방식을 도입했어요.

토스의 자체 React Native 번들러는 웹 생태계와 유사한 플러그인 구조를 갖추고 있어서, 번들러의 라이프사이클에 접근할 수 있어요. 이를 활용해 자동 타입 생성 플러그인을 만들었어요.

번들러가 `/pages` 폴더의 변경 사항을 감지하고, 새로운 페이지가 추가될 때마다 자동으로 타입을 등록하도록 만들었어요.

### 설정 파일 예제

자동 타입 생성을 사용하려면 번들러 설정에 `RouteGenPlugin` 플러그인을 추가하면 돼요.
    
    
    import { router } from "@granite-js/plugin-router";
    
    export default defineConfig({
      plugins: [router()],
    });

이제 `/pages` 폴더에 새로운 파일을 추가하면 자동으로 해당 페이지의 라우트와 타입이 생성돼요.

### 자동 타입 생성 방식

이 플러그인은 `chokidar` 나 `@parcel/watcher`를 활용해 `/pages` 폴더의 변경 사항을 실시간으로 감시할 수 있어요.

새로운 파일이 추가되면 이를 새로운 페이지로 인식하고, 자동으로 라우트와 타입을 생성해요. 즉, 파일명이 곧 페이지 경로가 되며, 기본적인 스캐폴딩 코드가 자동으로 생성돼요. 예를 들어, `pages/about.tsx` 파일을 만들면 자동으로 아래와 같은 코드가 생성돼요.

### 자동 생성되는 페이지 코드
    
    
    import React from 'react';
    import { Text, View } from 'react-native';
    import { createRoute } from '@granite-js/react-native';
    
    export const Route = createRoute('/about', {
      validateParams: (params) => params, // 현재는 검증 없음
      component: About,
    });
    
    export function About() {
      return (
        <View>
          <Text>Hello About</Text>
        </View>
      );
    }

### 자동 생성되는 타입 등록 코드

이 플러그인은 `/pages` 폴더의 변경 사항을 감지해 새로운 페이지가 추가될 때마다 자동으로 타입을 생성해요. 위에 언급한 대로 파일을\(`pages/about.tsx`\)를 만들면 아래와 같은 코드가 자동으로 등록돼요.
    
    
    import { Route as _AboutRoute } from '../pages/about';
    
    declare module '@granite-js/react-native' {
      interface RegisterScreen {
        '/about': ReturnType<typeof _AboutRoute.useParams>;
      }
    }

마찬가지로, `pages/page-b.tsx` 파일을 추가하면 `/page-b`에 대한 타입도 자동으로 반영돼요.
    
    
    import { Route as _AboutRoute } from '../pages/about';
    import { Route as _HomeRoute } from '../pages/home';
    
    declare module '@granite-js/react-native' {
      interface RegisterScreen {
        '/about': ReturnType<typeof _AboutRoute.useParams>;
        '/home': ReturnType<typeof _HomeRoute.useParams>;
      }
    }

하지만 `/pages` 폴더에 새 파일이 추가되었다고 무조건 타입을 추가하면 문제가 생길 수 있어요. 파일 내부에 `export const Route`가 정의되지 않은 경우가 있을 수 있기 때문이에요.

여기서 `Route`를 내보내는 방법은 크게 두 가지가 있어요.
    
    
    // 1. 선언 후 export
    const Route = createRoute(...);
    export { Route };
    
    // 2. 선언과 동시에 export
    export const Route = createRoute(...);

정규 표현식으로 문자열을 검사하면 코드 포맷에 따라 발생하는 예외 케이스\(예: 줄바꿈이나 공백 등\)를 처리하기 어려워요. 따라서 이를 해결하기 위해 SWC를 활용해 AST\(Abstract Syntax Tree\)를 분석해서, 파일이 실제로 `Route`를 내보내고 있는지 정확하게 확인해요.
    
    
    import { parseFileSync } from '@swc/core';
    
    /**
     * 파일에 Route가 export되어 있는지 확인합니다.
     */
    export function checkExportRoute(path: string) {
      try {
        const ast = parseFileSync(path, {
          syntax: 'typescript',
          tsx: true,
        });
    
        // export { Route } 형태 체크
        const hasExportSpecifiers = ast.body.some((node) => {
          if (node.type !== 'ExportNamedDeclaration') {
            return false;
          }
          return node.specifiers?.some((specifier) => {
            if (specifier.type !== 'ExportSpecifier') {
              return false;
            }
            return specifier.orig?.value === 'Route';
          });
        });
    
        if (hasExportSpecifiers) {
          return true;
        }
    
        // export const Route = ... 형태 체크
        const hasExportNamedVariable = ast.body.some((node) => {
          if (node.type !== 'ExportDeclaration') {
            return false;
          }
          if (node.declaration.type !== 'VariableDeclaration') {
            return false;
          }
    
          return node.declaration.declarations.some(
            (declaration) => declaration.id.type === 'Identifier' && declaration.id.value === 'Route'
          );
        });
    
        return hasExportNamedVariable;
      } catch {
        return false;
      }
    }

이런 방식을 통해, 개발자는 더 이상 별도로 타입을 수동 정의할 필요가 없어요. 단지 새로운 페이지를 추가하는 것만으로도 타입이 자동으로 관리되어 유지보수가 간편하고 라우팅 안정성이 높아져요.

## 4\. 타입-안전한 useNavigation 구현하기

기존의 `react-navigation`에서는 네비게이션 사용 시 페이지마다 명시적으로 타입을 선언해주어야 했습니다.

예를 들어 기존 방식은 아래와 같습니다:
    
    
    import { useNavigation, type NativeStackNavigationProp } from "@react-navigation/native";
    
    interface Screen {
      'page-a': { name: string },
      'page-b': undefined,
    }
    
    function PageB() {
      const navigation = useNavigation<NativeStackNavigationProp<Screen>>();
    
      return (
        <Button
          onPress={() => navigation.navigate("page-a", { name: "Toss" })}
          title="page-a 이동"
        />
      );
    }
    
    

### Granite에서의 개선된 접근법

Granite에서는 중앙에서 관리되는 타입 선언\(`RegisterScreen`\)을 선언 병합\(declaration merging\)하여, 모든 화면에서 자동으로 타입이 제공되도록 개선할 수 있습니다.

아래는 Granite의 개선된 `useNavigation` 훅 구현입니다:
    
    
    import {
      useNavigation as useNavigationNative,
      type NativeStackNavigationProp,
      ParamListBase
    } from "@react-navigation/native";
    
    export type NavigationProps = NativeStackNavigationProp<
      keyof RegisterScreen extendsnever ? ParamListBase : RegisterScreen
    >;
    
    export function useNavigation() {
      return useNavigationNative<NavigationProps>();
    }
    
    

개발자는 이제 별도의 제네릭을 매번 설정하지 않고도, 각 화면의 타입을 자동으로 정확하게 추론하여 사용할 수 있습니다.

### 타입 추론을 활용한 화면 이동 예시

다음과 같은 화면 이동 시, Granite이 제공하는 타입 추론으로 인해 파라미터의 타입이 자동 검증됩니다:
    
    
    import { createRoute, useNavigation } from '@granite-js/react-native';
    import { StyleSheet, View, Text, Pressable } from 'react-native';
    
    // Page B 라우트 정의
    export const Route = createRoute('/page-b', {
      validateParams: (params) => params, // 현재 검증 로직 없음
      component: PageB,
    });
    
    // Page B 컴포넌트
    function PageB() {
      const navigation = useNavigation();
    
      const handlePress = () => {
        navigation.navigate('/page-a', {
          name: "Toss", // '/page-a'에서 정의한 타입이 자동 적용됨
        });
      };
    
      return (
        <View style={[styles.container, { backgroundColor: '#3182f6' }]}>
          <Text style={styles.text}>Page B</Text>
          <Pressable onPress={handlePress}>
            <Text style={styles.buttonLabel}>A 페이지로 이동하기</Text>
          </Pressable>
        </View>
      );
    }
    
    

이제 잘못된 파라미터 값을 전달하면 컴파일 단계에서 오류가 즉시 발생하여, 개발자의 타입 안정성을 크게 높일 수 있습니다.

## 마무리하며

이 기능을 활용하면 React Native에서 화면 전환을 훨씬 더 안전하게 관리할 수 있어요. 화면의 경로를 문자열로 직접 입력하지 않고 타입으로 정의하기 때문에, 오타로 엉뚱한 화면으로 이동하는 일을 막을 수 있죠. 어떤 화면으로 이동할 수 있는지도 코드에서 바로 확인할 수 있어서 개발 생산성도 높아져요.

Granite은 iOS, Android, 프론트엔드 플랫폼 개발자들이 각자의 전문성을 살려 함께 RN Framework Team에서 만든 프로젝트예요. React Native 번들러부터 인프라까지 직접 구축해, 이 모든 걸 누구나 쓸 수 있도록 공개하는 게 목표예요.

장기적으로는 전 세계 React Native 개발자들이 함께 사용할 수 있는 모범 사례\(Best Practice\)가 되는 것을 지향하고 있어요. 더 나아가, 웹 개발자들도 네이티브 앱 개발에 쉽게 참여할 수 있도록 확장해 나갈 계획이에요\!

이 글의 최초 발행시에는 Bedrock이라는 이름으로 작성되었으나, 공개되면서 Granite로 변경되어 수정 반영했어요. Granite에 많은 관심 부탁드려요\!