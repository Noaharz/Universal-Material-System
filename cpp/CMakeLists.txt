cmake_minimum_required(VERSION 3.16)
project(ums_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(UMS_NO_FILESYSTEM "Build without filesystem IO (e.g. for WebAssembly)" OFF)

set(UMS_CORE_SOURCES
    src/units.cpp
    src/parser.cpp
    src/reader.cpp
    src/registry.cpp
    src/serializer.cpp
    src/validation.cpp
    src/writer.cpp
)

add_library(ums STATIC ${UMS_CORE_SOURCES})
target_include_directories(ums PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_compile_features(ums PUBLIC cxx_std_20)

enable_testing()

add_executable(ums_core_tests tests/core_test.cpp)
target_link_libraries(ums_core_tests PRIVATE ums)
add_test(NAME ums_core_tests COMMAND ums_core_tests)

if(UMS_NO_FILESYSTEM)
    target_compile_definitions(ums PUBLIC UMS_NO_FILESYSTEM)
else()
    target_sources(ums PRIVATE src/fileio.cpp src/library.cpp)

    add_executable(umsdump tools/umsdump.cpp)
    target_link_libraries(umsdump PRIVATE ums)

    add_executable(umsconf tools/umsconf.cpp)
    target_link_libraries(umsconf PRIVATE ums)

    add_executable(ums_tests tests/reader_test.cpp)
    target_link_libraries(ums_tests PRIVATE ums)
    add_test(NAME ums_tests COMMAND ums_tests ${CMAKE_CURRENT_SOURCE_DIR}/../library)
endif()
