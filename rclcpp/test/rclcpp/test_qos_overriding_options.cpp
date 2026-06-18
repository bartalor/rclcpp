// Copyright 2020 Open Source Robotics Foundation, Inc.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <atomic>
#include <memory>
#include <mutex>
#include <string>

#include "gmock/gmock.h"

#include "rclcpp/rclcpp.hpp"
#include "rclcpp/qos_overriding_options.hpp"
#include "test_msgs/msg/empty.hpp"

TEST(TestQosOverridingOptions, test_overriding_options) {
  auto options = rclcpp::QosOverridingOptions::with_default_policies();
  EXPECT_EQ(options.get_id(), "");
  EXPECT_EQ(options.get_validation_callback(), nullptr);
  EXPECT_THAT(
    options.get_policy_kinds(), testing::ElementsAre(
      rclcpp::QosPolicyKind::History,
      rclcpp::QosPolicyKind::Depth,
      rclcpp::QosPolicyKind::Reliability));
}

TEST(TestQosOverridingOptions, test_qos_policy_kind_to_cstr) {
  EXPECT_THROW(
    rclcpp::qos_policy_kind_to_cstr(rclcpp::QosPolicyKind::Invalid),
    std::invalid_argument);
}

// Regression tests for https://github.com/ros2/rclcpp/issues/2876
//
// Root cause (confirmed against the issue thread and the rclcpp source):
//
//   * declare_parameter() holds NodeParameters::mutex_ and, at declaration time,
//     fires the user's on-set parameter callback (__declare_parameter_common ->
//     __set_parameters_atomically_common).
//   * Creating a publisher/subscription with qos_overriding_options for the
//     FIRST time declares the internal qos_overrides.* parameters. If that
//     declaration happens from inside an on-set callback, the callback is
//     re-fired synchronously on the same stack.
//   * The reporter's real callback (Nav2 SmacPlannerHybrid) holds a plain
//     std::lock_guard<std::mutex> around the create_publisher. The re-entrant
//     fire re-takes that non-recursive lock on the same thread -> deadlock.
//
// The bug is a SAME-THREAD synchronous re-entry, so it is detected directly by
// observing the re-entry -- no real blocking lock, no worker thread, no timeout
// is needed (and taking a non-recursive lock twice on one thread, or try_lock on
// a mutex the thread already owns, is itself undefined behaviour). ReentryProbe
// bumps a depth counter on entry; if the callback is ever entered while already
// inside itself it records that re-entry happened and WHICH qos-override
// parameter triggered it. A regression then reports the exact mechanism --
// "re-fired the on-set callback while declaring qos_overrides...history" -- and
// the test still returns normally. No diagnostic prints: every fact needed to
// read a failure is in the EXPECT message. (A genuine future regression that
// truly blocked would be caught by the CTest TIMEOUT around the test.)

namespace
{

// Records the same-thread re-entry that constitutes the #2876 deadlock. The
// on-set callback bumps a depth counter on entry; entering while already inside
// itself (depth > 0) is the re-entrant fire triggered by the qos-override
// declaration, and the name of the parameter being declared is captured.
struct ReentryProbe
{
  std::atomic<int> depth{0};
  std::atomic<int> reentry_count{0};
  std::mutex name_mutex;
  std::string reentered_on_param;  // guarded by name_mutex

  // Call at the top of the callback with the parameters it received. Returns an
  // RAII guard that decrements the depth when the callback frame unwinds.
  [[nodiscard]] auto enter(const std::vector<rclcpp::Parameter> & params)
  {
    if (depth.fetch_add(1) > 0) {
      reentry_count.fetch_add(1);
      std::lock_guard<std::mutex> lock(name_mutex);
      if (reentered_on_param.empty() && !params.empty()) {
        reentered_on_param = params.front().get_name();
      }
    }
    struct DepthGuard
    {
      std::atomic<int> & d;
      ~DepthGuard() {d.fetch_sub(1);}
    };
    return DepthGuard{depth};
  }

  bool reentered() const {return reentry_count.load() > 0;}

  std::string where()
  {
    std::lock_guard<std::mutex> lock(name_mutex);
    return reentered_on_param;
  }
};

}  // namespace

// First-time publisher creation inside an on-set callback must not re-fire that
// callback: in Nav2 the callback holds a non-recursive lock, so a re-entrant fire
// re-takes it on the same thread and deadlocks.
TEST(TestQosOverridingOptions, create_publisher_in_param_callback_does_not_deadlock) {
  rclcpp::init(0, nullptr);
  auto node = std::make_shared<rclcpp::Node>("qos_override_pub_repro");

  std::atomic<bool> arm_creation{false};
  ReentryProbe probe;

  auto handle = node->add_on_set_parameters_callback(
    [&](const std::vector<rclcpp::Parameter> & params) {
      rcl_interfaces::msg::SetParametersResult result;
      result.successful = true;

      auto depth_guard = probe.enter(params);

      if (arm_creation.exchange(false)) {
        rclcpp::PublisherOptions pub_options;
        pub_options.qos_overriding_options =
        rclcpp::QosOverridingOptions::with_default_policies();
        auto pub = node->create_publisher<test_msgs::msg::Empty>(
          "repro_pub_topic", rclcpp::QoS(10), pub_options);
        (void)pub;
      }
      return result;
    });

  node->declare_parameter("trigger", 0);

  arm_creation.store(true);
  node->set_parameter(rclcpp::Parameter("trigger", 1));

  EXPECT_FALSE(probe.reentered())
    << "create_publisher with qos_overriding_options re-fired the on-set "
       "callback while declaring '" << probe.where() << "'; in Nav2 the callback "
       "holds a non-recursive lock, so this re-entry re-takes it on the same "
       "thread -> deadlock (https://github.com/ros2/rclcpp/issues/2876)";

  (void)handle;
  rclcpp::shutdown();
}

// Same scenario for a subscription -- the issue thread reports the deadlock for
// both publishers and subscriptions.
TEST(TestQosOverridingOptions, create_subscription_in_param_callback_does_not_deadlock) {
  rclcpp::init(0, nullptr);
  auto node = std::make_shared<rclcpp::Node>("qos_override_sub_repro");

  std::atomic<bool> arm_creation{false};
  ReentryProbe probe;

  auto handle = node->add_on_set_parameters_callback(
    [&](const std::vector<rclcpp::Parameter> & params) {
      rcl_interfaces::msg::SetParametersResult result;
      result.successful = true;

      auto depth_guard = probe.enter(params);

      if (arm_creation.exchange(false)) {
        rclcpp::SubscriptionOptions sub_options;
        sub_options.qos_overriding_options =
        rclcpp::QosOverridingOptions::with_default_policies();
        auto sub = node->create_subscription<test_msgs::msg::Empty>(
          "repro_sub_topic", rclcpp::QoS(10),
          [](test_msgs::msg::Empty::ConstSharedPtr) {}, sub_options);
        (void)sub;
      }
      return result;
    });

  node->declare_parameter("trigger", 0);

  arm_creation.store(true);
  node->set_parameter(rclcpp::Parameter("trigger", 1));

  EXPECT_FALSE(probe.reentered())
    << "create_subscription with qos_overriding_options re-fired the on-set "
       "callback while declaring '" << probe.where() << "'; in Nav2 the callback "
       "holds a non-recursive lock, so this re-entry re-takes it on the same "
       "thread -> deadlock (https://github.com/ros2/rclcpp/issues/2876)";

  (void)handle;
  rclcpp::shutdown();
}

// Re-creating a publisher whose qos-override parameters ALREADY exist must keep
// working: this hits the declare-or-get "get" branch and is the common Nav2
// re-initialization path. Guards against over-suppressing that branch.
TEST(TestQosOverridingOptions, recreate_publisher_in_param_callback_does_not_deadlock) {
  rclcpp::init(0, nullptr);
  auto node = std::make_shared<rclcpp::Node>("qos_override_recreate_repro");

  std::atomic<bool> arm_creation{false};
  ReentryProbe probe;

  // Create the publisher once OUTSIDE any callback so the qos-override params
  // are already declared; the callback then re-creates it (declare-or-get hits
  // the "get" branch).
  auto make_pub = [&]() {
      rclcpp::PublisherOptions pub_options;
      pub_options.qos_overriding_options =
        rclcpp::QosOverridingOptions::with_default_policies();
      return node->create_publisher<test_msgs::msg::Empty>(
        "repro_recreate_topic", rclcpp::QoS(10), pub_options);
    };
  auto first_pub = make_pub();
  (void)first_pub;

  auto handle = node->add_on_set_parameters_callback(
    [&](const std::vector<rclcpp::Parameter> & params) {
      rcl_interfaces::msg::SetParametersResult result;
      result.successful = true;
      auto depth_guard = probe.enter(params);
      if (arm_creation.exchange(false)) {
        auto pub = make_pub();
        (void)pub;
      }
      return result;
    });

  node->declare_parameter("trigger", 0);

  arm_creation.store(true);
  node->set_parameter(rclcpp::Parameter("trigger", 1));

  EXPECT_FALSE(probe.reentered())
    << "re-creating a publisher whose qos-override parameters already exist "
       "re-fired the on-set callback while handling '" << probe.where()
    << "'; the declare-or-get \"get\" branch must not re-fire it "
       "(https://github.com/ros2/rclcpp/issues/2876)";

  (void)handle;
  rclcpp::shutdown();
}
