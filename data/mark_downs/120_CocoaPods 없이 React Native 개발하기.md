# CocoaPods 없이 React Native 개발하기

**Date:** 2024년 11월 6일
**URL:** https://toss.tech/article/react-native-without-cocoapods

---

프로젝트에 React Native를 도입할 때 크게 두 가지 방식이 있습니다.

  1. 프로젝트를 처음부터 React Native 로 개발한다.
  2. 현재 프로젝트에 부분적으로 React Native 를 도입한다.

베트남의 토스앱을 개발하던 때는 운영되는 서비스를 잠시 멈추고 [React Native로 새로 개발했었습니다](https://www.youtube.com/watch?v=b_6CjuvVg8o). 그 시점에 앱의 기능이 그렇게 많지 않았기 때문에 가능했었습니다. 하지만 한국에서 서비스 하고 있는 토스앱은 그렇지 않았습니다.

## 토스의 React Native 도입 배경

토스앱은 사실 크로스 플랫폼을 활용하기 위해 React Native를 도입했던 것은 아니었습니다. 2021년 코로나가 극심할 때 식당이나 카페등 가게에 출입하기 위해 QR인증을 했던 것을 기억하실것입니다. 그 때 QR인증을 위해 나라에서 지정한 업체의 SDK 를 사용해야 했습니다. 그런데 그 업체가 React Native로 된 SDK를 전달해주었고, 그렇게 토스앱에 React Native가 포함되었습니다. 

이후 토스 내부에서도 웹서비스의 화면들을 더 빠르게 로드해야 한다는 요구사항과 겹쳐서 React를 다루는 Frontend 개발자들이 앱에 포함되어 있는 React Native를 살려 크로스 플랫폼 도구로 사용하게 되었습니다.

토스와 비슷하게 많은 회사들이 각자 다른 이유로 운영 중인 서비스를 크로스 플랫폼으로 확장하고자 React Native를 도입하려고 할 것입니다. 이런 경우에 CocoaPods를 사용하지 않고 React Native를 도입하는 방법을 알려드리겠습니다. 

## React Native와 의존성 관리 도구

운영되는 앱에 React Native를 도입하기로 결정했을 때 iOS 개발자의 입장을 생각해봅시다. React Native는 기본적으로 CocoaPods로 설치되도록 되어 있어요. 현재 운영하고 있는 서비스가 CocoaPods를 의존성 관리 도구로 사용하고 있다면, 큰 어려움 없이 React Native를 도입할 수 있습니다.

하지만 iOS 개발 환경에는 CocoaPods 외에도 여러 가지의 의존성 관리 도구가 있습니다. 애플의 First Party인 Swift Package Manager 나, Carthage, Rome, 등등이 있습니다. 의존성 관리 도구는 아니지만 프로젝트 설정 관리 도구인 Tuist도 있습니다.

그럼 CocoaPods 외에 다른 의존성 관리 도구를 사용하고 있다면 어떻게 React Native를 도입할 수 있을까요? 사용 중인 의존성 관리 도구와 CocoaPods를 함께 사용해야 합니다. CocoaPods를 사용하고 있지 않다면 CocoaPods를 추가하면 되고, CocoaPods를 이미 병행으로 사용하고 있다면 해당 Podfile에 React Native 관련 의존성을 추가하면 됩니다. 

하지만 이렇게 의존성 관리 도구를 병행하는 것은 좋은 방법이 아닙니다.

## 왜 의존성 관리 도구를 하나만 써야 할까?

두 가지 이상의 의존성 관리 도구를 사용한다면 각각의 의존성 관리 도구는 각자가 관리하는 의존성들만 Resolve할 뿐, 서로가 관리하고 있는 의존성을 알 수 없습니다. 즉 CocoaPods에서 A라는 라이브러리를 추가하고, Swift Package Manager 에서 A라는 라이브러리를 추가하면 라이브러리 A가 중복됩니다. 

라이브러리 B가 라이브러리 A에 의존하고, 라이브러리 C가 라이브러리 A에 의존한다고 생각해볼게요. 

이때 라이브러리 B를 CocoaPods에, 그리고 라이브러리 C를 Swift Package Manager에 추가하여 관리한다면 다음 그림처럼 됩니다. 

이처럼 라이브러리 A가 중복되고 빌드나 아카이브에 실패합니다. 

이 문제를 해결하기 위해 강제로 B가 A에 의존하지 않도록 해야 합니다. 그러기 위해 해야 하는 작업은 다음과 같습니다.

  * 라이브러리 B 의 레포를 찾아 Fork 한다.
  * Fork 한 레포에서 podspec 파일을 찾는다.
  * podspec 파일에서 라이브러리 A에 대한 의존성 항목을 찾아서 삭제한다. 
  * Podfile에서 라이브러리 B의 레포 경로를 내가 수정한 레포지토리로 지정한다.

이러한 작업을 울며 겨자먹기로 할 수밖에 없습니다. 

하지만 이런 경우엔 의존성 커스텀 히스토리를 잘 관리해야 합니다. 그렇지 않으면 지뢰가 되어 추후에 문제가 생길 수 있기 때문이에요. 

  * Swift Package Manager에서 라이브러리 C가 더 이상 필요하지 않아 제거하게 되면 라이브러리 A도 함께 사라지기 때문에 라이브러리 B가 바라보던 라이브러리 A도 사라져 빌드에 실패하게 됩니다. 

    * 나중에 이 히스토리를 모르는 다른 사람이 fork한 레포를 사용하지 않고 원본 레포를 사용한다면 A 라이브러리 중복 문제가 다시 나타나고, 원인을 알기 어려워 시간을 허비하게 됩니다.

이처럼 히스토리를 모르면 해결하기 어려운 문제들이 일어납니다. 그렇기 때문에 히스토리를 잘 관리하거나, 의존성 관리 도구는 하나만 사용하는 것이 좋습니다. 

## CocoaPods 없이 React Native 라이브러리 포함하기

지금까지 의존성 관리 도구를 하나만 사용해야 되는 이유를 설명해드렸습니다. 그렇다면 이미 운영 중인 서비스의 의존성 관리 도구로 반드시 CocoaPods를 사용해야 될까요? 이제부터는 CocoaPods를 사용하지 않고 하나의 의존성 관리 도구로 React Native를 도입할 수 있는 방법을 알려드리겠습니다. 

React Native 라이브러리들을 미리 XCFramework로 빌드한 다음에 내 프로젝트에 포함하면 됩니다. 미리 빌드 하는 과정에서 사실은 CocoaPods를 여전히 사용하게 됩니다. 이 방법을 Prebuild 라 부르겠습니다. 

## 따라해보기

그렇다면 이제 ReactNative를 XCFramework로 빌드 하는 방법을 단계별로 알아보겠습니다.

  1. 스크립트를 이용해 프로젝트를 만듭니다.

     * `react_native_prebuild` 디렉토리를 생성 후 진입합니다.
           
           mkdir react_native_prebuild
           cd react_native_prebuild

     * 프로젝트 생성 스크립트를 만듭니다. 
           
           gem install xcodeproj
           echo "require 'xcodeproj'
           
           # 새로운 프로젝트 생성
           project = Xcodeproj::Project.new('ReactNativePrebuild.xcodeproj')
           
           # 타겟 추가
           project.new_target(:application, 'ReactNativePrebuild', :ios)
           
           # 프로젝트 저장
           project.save" > create_project.rb

     * 프로젝트 생성 스크립트를 실행해 프로젝트를 생성합니다.
           
           ruby create_project.rb

  2. `react-native`를 설치할 `package.json`을 만듭니다.
         
         {
           "name": "react-native-prebuild",
           "version": "0.0.1",
           "private": true,
           "dependencies": {
             "react": "18.3.1",
             "react-native": "0.76.0", 
             "yarn": "^1.22.2"
           }
         }

  3. yarn 등으로 설치합니다. 

yarn 이 없는 경우 
         
         npm install --global yarn

yarn 으로 빌드
         
         yarn

  4. `pod init`을 수행합니다.
         
         pod init

  5. `podfile`을 다음과 같이 수정합니다. 
         
         source 'https://cdn.cocoapods.org/'
         platform :ios, '18.0'
         
         # prepare_react_native_project 를 호출하기 위함.
         require_relative './node_modules/react-native/scripts/react_native_pods'
         
         inhibit_all_warnings!
         prepare_react_native_project!
         
         target 'ReactNativePrebuild' do
           use_frameworks! :linkage => :static
         
           use_react_native!(
             :path => './node_modules/react-native',
             :app_path => "#{Pod::Config.instance.installation_root}/"
           )
         
         end
         
         post_install do |installer|
           # For ReactNative
           react_native_post_install(
               installer,
               './node_modules/react-native',
               :mac_catalyst_enabled => false
             )
         
         end

  6. `pod install`로 pod을 설치합니다. 
         
         pod install

  7. React Native 라이브러리들을 XCFramework 로 빌드 하는 스크립트를 작성합니다. 
         
         touch build_xcframeworks.sh
         chmod +x build_xcframeworks.sh

빌드 스크립트의 내용은 다음과 같습니다. 

     * 라이브러리를 simulator 용으로 archive 합니다.
     * 라이브러리를 device 용으로 archive 합니다.
     * 라이브러리들의 framework들을 뽑아 XCFramework로 만듭니다.
    
    #!/bin/bash
    
    set -euo pipefail
    
    export SRCROOT=$(pwd)
    export WORKSPACE=ReactNativePrebuild
    export PROJECT="Pods-$WORKSPACE"
    
    function archive() {
      xcodebuild archive \
        -workspace $WORKSPACE.xcworkspace \
        -scheme $PROJECT \
        -archivePath $SRCROOT/$PROJECT-iphonesimulator.xcarchive \
        -configuration $1 \
        -sdk iphonesimulator \
        -quiet \
        SKIP_INSTALL=NO
      xcodebuild archive \
        -workspace $WORKSPACE.xcworkspace \
        -scheme $PROJECT \
        -archivePath $SRCROOT/$PROJECT-iphoneos.xcarchive \
        -configuration $1 \
        -sdk iphoneos \
        -quiet \
        SKIP_INSTALL=NO
    }
    
    function create_xcframework() {
        for framework in $(find $SRCROOT/$PROJECT-iphonesimulator.xcarchive/Products/Library/Frameworks -type d -name "*.framework");
        do
            basename=$(basename $framework)
            framework_name=$(basename $framework .framework)
    
            xcodebuild -create-xcframework \
                -framework "$SRCROOT/$PROJECT-iphonesimulator.xcarchive/Products/Library/Frameworks/$basename" \
                -framework "$SRCROOT/$PROJECT-iphoneos.xcarchive/Products/Library/Frameworks/$basename" \
                -output "$SRCROOT/Frameworks/$framework_name.xcframework"
        done
    
        copyCommonFramworks
    }
    
    function copyCommonFramworks() {
      cp -R $SRCROOT/Pods/hermes-engine/destroot/Library/Frameworks/universal/hermes.xcframework $SRCROOT/Frameworks/hermes.xcframework
    }
    
    function clean() {
        rm -rf $SRCROOT/$PROJECT-iphoneos.xcarchive
        rm -rf $SRCROOT/$PROJECT-iphonesimulator.xcarchive
        rm -rf Pods
        rm -rf node_modules
    }
    
    function build_and_create_frameworks() {
        local configuration="Release"
        rm -rf build
        yarn
        pod install
        archive $configuration
        create_xcframework
        clean
    }
    
    function initDirectory() {
        rm -rf $SRCROOT/Frameworks
        rm -rf $SRCROOT/Sources
        mkdir $SRCROOT/Frameworks
        mkdir Sources
        touch Sources/dummy.swift
    }
    
    initDirectory
    build_and_create_frameworks 
    ruby ./generate_package_swift.rb

  8. `package.swift` 를 생성하는 스크립트 파일 `generate_package_swift.rb` 를 만듭니다.
         
         touch generate_package_swift.rb
         
         frameworks_dir = 'Frameworks'
         
         frameworks = Dir.entries(frameworks_dir).select { |entry| entry.end_with?('.xcframework') }
         
         framework_names = frameworks.map { |f| File.basename(f, '.xcframework') }
         
         package_swift_content = <<~SWIFT
           // swift-tools-version:5.6
           import PackageDescription
         
           let package = Package(
               name: "PrebuiltReactNativeFrameworks",
               platforms: [
                   .iOS(.v11)
               ],
               products: [
                   .library(
                       name: "PrebuiltReactNativeFrameworks",
                       targets: ["PrebuiltReactNativeFrameworks"]
                   )
               ],
               targets: [
                   // 메인 타겟: 모든 프레임워크를 포함
                   .target(
                       name: "PrebuiltReactNativeFrameworks",
                       dependencies: [
         SWIFT
         
         framework_names.each_with_index do |name, index|
           comma = index < framework_names.size - 1 ? ',' : ''
           package_swift_content << "                  \"#{name}\"#{comma}\n"
         end
         
         package_swift_content << <<~SWIFT
                       ],
                       path: "Sources/",
                       sources: ["dummy.swift"],
                       linkerSettings: [
                           .linkedLibrary("objc"),
                           .linkedLibrary("c++"),
                           .linkedLibrary("c++abi"),
                           .linkedFramework("JavaScriptCore", .when(platforms: [.iOS])),
                       ]
                   ),
         SWIFT
         
         framework_names.each_with_index do |name, index|
           comma = index < framework_names.size - 1 ? ',' : ''
           package_swift_content << <<~SWIFT
                   .binaryTarget(
                       name: "#{name}",
                       path: "Frameworks/#{name}.xcframework"
                   )#{comma}
           SWIFT
         end
         
         package_swift_content << <<
         
         

  9. `build_xcframeworks.sh` 스크립트를 를 수행하여 XCFramework들과 `package.swift`를 생성합니다.`swift build `명령어로 완성된 `package.swift`가 잘 생성되었는지 확인해보면 좋습니다. 
  10. 완성된 Swift Package를 운영중인 프로젝트에 추가합니다.

  11. React 가 import 되는것을 확인합니다. 

## Prebuild의 장점

iOS 개발자에게 가장 큰 적은 빌드 시간입니다. 프로젝트의 복잡성이 증가할수록 빌드 시간도 기하급수적으로 증가합니다. 그래서 iOS 개발자에게 좋은 코드란 읽고 이해하기 좋거나 기능의 추가, 수정이 용이하는 등 아키텍처 측면에서 아름다운 것 외에도 빠르게 빌드 되는 코드라는 중요한 요소가 있습니다. 

CocoaPods를 이용해 React Native를 추가한다면 라이브러리들의 버전을 Resolve하는 시간, Fetch하는 시간이 걸리게 되고 첫 빌드 시 React Native 코드도 함께 빌드되어야 실행을 해볼 수 있습니다. 이론상 CocoaPods로 추가된 코드들은 처음 한 번만 빌드 되고 증분 빌드 시엔 다시 빌드 되지 않지만, 알 수 없는 원인으로 다시 빌드 시간이 소요되는 경우도 있습니다. 또한 Clean Build를 할 경우 명백하게 다시 빌드 시간이 소요됩니다.

만약 이 빌드 시간이 사라질 수 있다면 어떨까요? 예를 들어 1분의 시간이 절약되면, 하루 평균 `checkout 횟수 * 개발자 수` 의 시간이 매일 절약됩니다. 평균 checkout 횟수가 5회이고 개발자가 10명일 경우 하루에 50분의 시간이 절약되고, 한 달이면 1000분으로 16시간이 절약됩니다. 하지만 1분에서 멈추지 않고, 2분이 줄어들고 개발자가 20명이면 한 달에 4000분, 즉 66시간이 절약되게 됩니다. 

## 맺음말

이상 의존성 관리 도구를 하나만 사용해야 하는 이유, CocoaPods를 사용하지 않고 React Native를 iOS 환경에서 이용하는 방법, Prebuild를 사용하였을 때의 장점에 대해서 알아보았습니다. 이 방법을 사용하여 여러분도 의존성 관리 도구를 여러 개 사용하지 않고, 더 빠르게 빌드할 수 있길 바랍니다.