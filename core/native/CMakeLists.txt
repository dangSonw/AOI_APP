cmake_minimum_required(VERSION 3.18)
project(aoi_core LANGUAGES CXX)

add_library(aoi_core INTERFACE)
target_include_directories(aoi_core INTERFACE /include)
