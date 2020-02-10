/*
 * Copyright (C) 2019-2020 Open Source Robotics Foundation
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
*/

#ifndef SCENARIO_H
#define SCENARIO_H

#include "polygon.h"
#include "vertex.h"

#include <map>
#include <string>
#include <yaml-cpp/yaml.h>

class Scenario
{
public:
  std::string name;
  std::string filename;
  std::vector<Vertex> vertices;
  std::map<std::string, Polygon> roi;  // region of interest on each level

  /////////////////////////////////
  Scenario();
  ~Scenario();

  bool load();
  bool save() const;
};

#endif
