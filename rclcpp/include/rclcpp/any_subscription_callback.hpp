// Copyright 2014 Open Source Robotics Foundation, Inc.
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

#ifndef RCLCPP__ANY_SUBSCRIPTION_CALLBACK_HPP_
#define RCLCPP__ANY_SUBSCRIPTION_CALLBACK_HPP_

#include <atomic>
#include <functional>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <type_traits>
#include <utility>

#include "rosidl_runtime_cpp/traits.hpp"
#include "tracetools/tracetools.h"
#include "tracetools/utils.hpp"

#include "rclcpp/allocator/allocator_common.hpp"
#include "rclcpp/detail/subscription_callback_type_helper.hpp"
#include "rclcpp/function_traits.hpp"
#include "rclcpp/message_info.hpp"
#include "rclcpp/serialization.hpp"
#include "rclcpp/serialized_message.hpp"
#include "rclcpp/type_adapter.hpp"

namespace rclcpp
{

namespace detail
{

template<typename MessageT, typename AllocatorT>
struct MessageDeleterHelper
{
  using AllocTraits = allocator::AllocRebind<MessageT, AllocatorT>;
  using Alloc = typename AllocTraits::allocator_type;
  using Deleter = allocator::Deleter<Alloc, MessageT>;
};

/// Struct which contains all possible callback signatures, with or without a TypeAdapter.
template<typename MessageT, typename AllocatorT>
struct AnySubscriptionCallbackPossibleTypes
{
  /// MessageT::custom_type if MessageT is a TypeAdapter, otherwise just MessageT.
  using SubscribedType = typename rclcpp::TypeAdapter<MessageT>::custom_type;
  /// MessageT::ros_message_type if MessageT is a TypeAdapter, otherwise just MessageT.
  using ROSMessageType = typename rclcpp::TypeAdapter<MessageT>::ros_message_type;

  using SubscribedMessageDeleter =
    typename MessageDeleterHelper<SubscribedType, AllocatorT>::Deleter;
  using ROSMessageDeleter =
    typename MessageDeleterHelper<ROSMessageType, AllocatorT>::Deleter;
  using SerializedMessageDeleter =
    typename MessageDeleterHelper<rclcpp::SerializedMessage, AllocatorT>::Deleter;

  using ConstRefCallback =
    std::function<void (const SubscribedType &)>;
  using ConstRefROSMessageCallback =
    std::function<void (const ROSMessageType &)>;
  using ConstRefWithInfoCallback =
    std::function<void (const SubscribedType &, const rclcpp::MessageInfo &)>;
  using ConstRefWithInfoROSMessageCallback =
    std::function<void (const ROSMessageType &, const rclcpp::MessageInfo &)>;
  using ConstRefSerializedMessageCallback =
    std::function<void (const rclcpp::SerializedMessage &)>;
  using ConstRefSerializedMessageWithInfoCallback =
    std::function<void (const rclcpp::SerializedMessage &, const rclcpp::MessageInfo &)>;

  using UniquePtrCallback =
    std::function<void (std::unique_ptr<SubscribedType, SubscribedMessageDeleter>)>;
  using UniquePtrROSMessageCallback =
    std::function<void (std::unique_ptr<ROSMessageType, ROSMessageDeleter>)>;
  using UniquePtrWithInfoCallback =
    std::function<void (
        std::unique_ptr<SubscribedType, SubscribedMessageDeleter>,
        const rclcpp::MessageInfo &)>;
  using UniquePtrWithInfoROSMessageCallback =
    std::function<void (
        std::unique_ptr<ROSMessageType, ROSMessageDeleter>,
        const rclcpp::MessageInfo &)>;
  using UniquePtrSerializedMessageCallback =
    std::function<void (std::unique_ptr<rclcpp::SerializedMessage, SerializedMessageDeleter>)>;
  using UniquePtrSerializedMessageWithInfoCallback =
    std::function<void (
        std::unique_ptr<rclcpp::SerializedMessage, SerializedMessageDeleter>,
        const rclcpp::MessageInfo &)>;

  using SharedConstPtrCallback =
    std::function<void (std::shared_ptr<const SubscribedType>)>;
  using SharedConstPtrROSMessageCallback =
    std::function<void (std::shared_ptr<const ROSMessageType>)>;
  using SharedConstPtrWithInfoCallback =
    std::function<void (
        std::shared_ptr<const SubscribedType>,
        const rclcpp::MessageInfo &)>;
  using SharedConstPtrWithInfoROSMessageCallback =
    std::function<void (
        std::shared_ptr<const ROSMessageType>,
        const rclcpp::MessageInfo &)>;
  using SharedConstPtrSerializedMessageCallback =
    std::function<void (std::shared_ptr<const rclcpp::SerializedMessage>)>;
  using SharedConstPtrSerializedMessageWithInfoCallback =
    std::function<void (
        std::shared_ptr<const rclcpp::SerializedMessage>,
        const rclcpp::MessageInfo &)>;

  using ConstRefSharedConstPtrCallback =
    std::function<void (const std::shared_ptr<const SubscribedType> &)>;
  using ConstRefSharedConstPtrROSMessageCallback =
    std::function<void (const std::shared_ptr<const ROSMessageType> &)>;
  using ConstRefSharedConstPtrWithInfoCallback =
    std::function<void (
        const std::shared_ptr<const SubscribedType> &,
        const rclcpp::MessageInfo &)>;
  using ConstRefSharedConstPtrWithInfoROSMessageCallback =
    std::function<void (
        const std::shared_ptr<const ROSMessageType> &,
        const rclcpp::MessageInfo &)>;
  using ConstRefSharedConstPtrSerializedMessageCallback =
    std::function<void (const std::shared_ptr<const rclcpp::SerializedMessage> &)>;
  using ConstRefSharedConstPtrSerializedMessageWithInfoCallback =
    std::function<void (
        const std::shared_ptr<const rclcpp::SerializedMessage> &,
        const rclcpp::MessageInfo &)>;

  // Deprecated signatures:
  using SharedPtrCallback =
    std::function<void (std::shared_ptr<SubscribedType>)>;
  using SharedPtrROSMessageCallback =
    std::function<void (std::shared_ptr<ROSMessageType>)>;
  using SharedPtrWithInfoCallback =
    std::function<void (std::shared_ptr<SubscribedType>, const rclcpp::MessageInfo &)>;
  using SharedPtrWithInfoROSMessageCallback =
    std::function<void (
        std::shared_ptr<ROSMessageType>,
        const rclcpp::MessageInfo &)>;
  using SharedPtrSerializedMessageCallback =
    std::function<void (std::shared_ptr<rclcpp::SerializedMessage>)>;
  using SharedPtrSerializedMessageWithInfoCallback =
    std::function<void (std::shared_ptr<rclcpp::SerializedMessage>, const rclcpp::MessageInfo &)>;
};

}  // namespace detail

template<
  typename MessageT,
  typename AllocatorT = std::allocator<void>
>
class AnySubscriptionCallback
{
private:
  /// MessageT::custom_type if MessageT is a TypeAdapter, otherwise just MessageT.
  using SubscribedType = typename rclcpp::TypeAdapter<MessageT>::custom_type;
  /// MessageT::ros_message_type if MessageT is a TypeAdapter, otherwise just MessageT.
  using ROSMessageType = typename rclcpp::TypeAdapter<MessageT>::ros_message_type;

  using SubscribedTypeDeleterHelper =
    rclcpp::detail::MessageDeleterHelper<SubscribedType, AllocatorT>;
  using SubscribedTypeAllocatorTraits = typename SubscribedTypeDeleterHelper::AllocTraits;
  using SubscribedTypeAllocator = typename SubscribedTypeDeleterHelper::Alloc;
  using SubscribedTypeDeleter = typename SubscribedTypeDeleterHelper::Deleter;

  using ROSMessageTypeDeleterHelper =
    rclcpp::detail::MessageDeleterHelper<ROSMessageType, AllocatorT>;
  using ROSMessageTypeAllocatorTraits = typename ROSMessageTypeDeleterHelper::AllocTraits;
  using ROSMessageTypeAllocator = typename ROSMessageTypeDeleterHelper::Alloc;
  using ROSMessageTypeDeleter = typename ROSMessageTypeDeleterHelper::Deleter;

  using SerializedMessageDeleterHelper =
    rclcpp::detail::MessageDeleterHelper<rclcpp::SerializedMessage, AllocatorT>;
  using SerializedMessageAllocatorTraits = typename SerializedMessageDeleterHelper::AllocTraits;
  using SerializedMessageAllocator = typename SerializedMessageDeleterHelper::Alloc;
  using SerializedMessageDeleter = typename SerializedMessageDeleterHelper::Deleter;

  using CallbackTypes = detail::AnySubscriptionCallbackPossibleTypes<MessageT, AllocatorT>;

  // The four dispatch entry signatures, type-erased into std::function. Each
  // set(...) overload populates these from the user's typed callback via
  // adapter lambdas. The variant-of-16 callback shapes the class used to hold
  // is collapsed into these four shapes plus two routing bools (see below).
  using RosDispatchFn =
    std::function<void(std::shared_ptr<ROSMessageType>, const rclcpp::MessageInfo &)>;
  using SerializedDispatchFn =
    std::function<void(
        std::shared_ptr<const rclcpp::SerializedMessage>,
        const rclcpp::MessageInfo &)>;
  using IntraSharedDispatchFn =
    std::function<void(std::shared_ptr<const SubscribedType>, const rclcpp::MessageInfo &)>;
  using IntraUniqueDispatchFn =
    std::function<void(
        std::unique_ptr<SubscribedType, SubscribedTypeDeleter>,
        const rclcpp::MessageInfo &)>;

public:
  explicit
  AnySubscriptionCallback(const AllocatorT & allocator = AllocatorT())  // NOLINT[runtime/explicit]
  : subscribed_type_allocator_(allocator),
    ros_message_type_allocator_(allocator)
  {
    allocator::set_allocator_for_deleter(&subscribed_type_deleter_, &subscribed_type_allocator_);
    allocator::set_allocator_for_deleter(&ros_message_type_deleter_, &ros_message_type_allocator_);
  }

  AnySubscriptionCallback(const AnySubscriptionCallback & other)
  : dispatch_ros_(other.dispatch_ros_),
    dispatch_serialized_(other.dispatch_serialized_),
    dispatch_intra_shared_(other.dispatch_intra_shared_),
    dispatch_intra_unique_(other.dispatch_intra_unique_),
    is_serialized_(other.is_serialized_),
    use_take_shared_(other.use_take_shared_),
    callback_disabled_(other.callback_disabled_.load()),
    subscribed_type_allocator_(other.subscribed_type_allocator_),
    subscribed_type_deleter_(other.subscribed_type_deleter_),
    ros_message_type_allocator_(other.ros_message_type_allocator_),
    ros_message_type_deleter_(other.ros_message_type_deleter_),
    serialized_message_allocator_(other.serialized_message_allocator_),
    serialized_message_deleter_(other.serialized_message_deleter_)
  {
    allocator::set_allocator_for_deleter(&subscribed_type_deleter_, &subscribed_type_allocator_);
    allocator::set_allocator_for_deleter(&ros_message_type_deleter_, &ros_message_type_allocator_);
  }

  /// Generic function for setting the callback.
  /**
   * There are specializations that overload this in order to deprecate some
   * callback signatures, and also to fix ambiguity between shared_ptr and
   * unique_ptr callback signatures when using them with lambda functions.
   */
  template<typename CallbackT>
  AnySubscriptionCallback<MessageT, AllocatorT>
  set(CallbackT callback)
  {
    // Use the SubscriptionCallbackTypeHelper to determine the actual type of
    // the CallbackT, in terms of std::function<...>, which does not happen
    // automatically with lambda functions in cases where the arguments can be
    // converted to one another, e.g. shared_ptr and unique_ptr.
    using scbth = detail::SubscriptionCallbackTypeHelper<MessageT, CallbackT>;
    using FT = typename scbth::callback_type;

    // Determine if the given CallbackT is a deprecated signature or not.
    constexpr auto is_deprecated =
      rclcpp::function_traits::same_arguments<
      FT,
      std::function<void(std::shared_ptr<SubscribedType>)>
      >::value ||
      rclcpp::function_traits::same_arguments<
      FT,
      std::function<void(std::shared_ptr<SubscribedType>, const rclcpp::MessageInfo &)>
      >::value ||
      rclcpp::function_traits::same_arguments<
      FT,
      std::function<void(std::shared_ptr<ROSMessageType>)>
      >::value ||
      rclcpp::function_traits::same_arguments<
      FT,
      std::function<void(std::shared_ptr<ROSMessageType>, const rclcpp::MessageInfo &)>
      >::value ||
      rclcpp::function_traits::same_arguments<
      FT,
      std::function<void(std::shared_ptr<rclcpp::SerializedMessage>)>
      >::value ||
      rclcpp::function_traits::same_arguments<
      FT,
      std::function<void(std::shared_ptr<rclcpp::SerializedMessage>, const rclcpp::MessageInfo &)>
      >::value;

    if constexpr (is_deprecated) {
      set_deprecated(static_cast<FT>(callback));
    } else {
      install_typed_(static_cast<FT>(callback));
    }
    register_callback_for_tracing_(callback);

    // Return copy of self for easier testing, normally will be compiled out.
    return *this;
  }

  /// Function for shared_ptr to non-const MessageT, which is deprecated.
  template<typename SetT>
  // *INDENT-OFF*
  #if !defined(RCLCPP_AVOID_DEPRECATIONS_FOR_UNIT_TESTS)
  // suppress deprecation warnings in `test_any_subscription_callback.cpp`
  [[deprecated("use 'void(std::shared_ptr<const MessageT>)' instead")]]
  #endif
  // *INDENT-ON*
  void
  set_deprecated(std::function<void(std::shared_ptr<SetT>)> callback)
  {
    install_typed_(callback);
  }

  /// Function for shared_ptr to non-const MessageT with MessageInfo, which is deprecated.
  template<typename SetT>
  // *INDENT-OFF*
  #if !defined(RCLCPP_AVOID_DEPRECATIONS_FOR_UNIT_TESTS)
  // suppress deprecation warnings in `test_any_subscription_callback.cpp`
  [[deprecated(
          "use 'void(std::shared_ptr<const MessageT>, const rclcpp::MessageInfo &)' instead"
  )]]
  #endif
  // *INDENT-ON*
  void
  set_deprecated(std::function<void(std::shared_ptr<SetT>, const rclcpp::MessageInfo &)> callback)
  {
    install_typed_(callback);
  }

  /// Disable the callback from being called during dispatch.
  void disable()
  {
    std::unique_lock<std::recursive_mutex> callback_lock(callback_mutex_);
    callback_disabled_.store(true);
  }

  /// Enable the callback to be called during dispatch.
  void enable()
  {
    std::unique_lock<std::recursive_mutex> callback_lock(callback_mutex_);
    callback_disabled_.store(false);
  }

  std::unique_ptr<ROSMessageType, ROSMessageTypeDeleter>
  create_ros_unique_ptr_from_ros_shared_ptr_message(
    const std::shared_ptr<const ROSMessageType> & message)
  {
    auto ptr = ROSMessageTypeAllocatorTraits::allocate(ros_message_type_allocator_, 1);
    ROSMessageTypeAllocatorTraits::construct(ros_message_type_allocator_, ptr, *message);
    return std::unique_ptr<ROSMessageType, ROSMessageTypeDeleter>(ptr, ros_message_type_deleter_);
  }

  std::unique_ptr<rclcpp::SerializedMessage, SerializedMessageDeleter>
  create_serialized_message_unique_ptr_from_shared_ptr(
    const std::shared_ptr<const rclcpp::SerializedMessage> & serialized_message)
  {
    auto ptr = SerializedMessageAllocatorTraits::allocate(serialized_message_allocator_, 1);
    SerializedMessageAllocatorTraits::construct(
      serialized_message_allocator_, ptr, *serialized_message);
    return std::unique_ptr<
      rclcpp::SerializedMessage,
      SerializedMessageDeleter
    >(ptr, serialized_message_deleter_);
  }

  std::unique_ptr<SubscribedType, SubscribedTypeDeleter>
  create_custom_unique_ptr_from_custom_shared_ptr_message(
    const std::shared_ptr<const SubscribedType> & message)
  {
    auto ptr = SubscribedTypeAllocatorTraits::allocate(subscribed_type_allocator_, 1);
    SubscribedTypeAllocatorTraits::construct(subscribed_type_allocator_, ptr, *message);
    return std::unique_ptr<SubscribedType, SubscribedTypeDeleter>(ptr, subscribed_type_deleter_);
  }

  std::unique_ptr<SubscribedType, SubscribedTypeDeleter>
  convert_ros_message_to_custom_type_unique_ptr(const ROSMessageType & msg)
  {
    if constexpr (rclcpp::TypeAdapter<MessageT>::is_specialized::value) {
      auto ptr = SubscribedTypeAllocatorTraits::allocate(subscribed_type_allocator_, 1);
      SubscribedTypeAllocatorTraits::construct(subscribed_type_allocator_, ptr);
      rclcpp::TypeAdapter<MessageT>::convert_to_custom(msg, *ptr);
      return std::unique_ptr<SubscribedType, SubscribedTypeDeleter>(ptr, subscribed_type_deleter_);
    } else {
      throw std::runtime_error(
              "convert_ros_message_to_custom_type_unique_ptr "
              "unexpectedly called without TypeAdapter");
    }
  }

  std::unique_ptr<ROSMessageType, ROSMessageTypeDeleter>
  convert_custom_type_to_ros_message_unique_ptr(const SubscribedType & msg)
  {
    if constexpr (rclcpp::TypeAdapter<MessageT>::is_specialized::value) {
      auto ptr = ROSMessageTypeAllocatorTraits::allocate(ros_message_type_allocator_, 1);
      ROSMessageTypeAllocatorTraits::construct(ros_message_type_allocator_, ptr);
      rclcpp::TypeAdapter<MessageT>::convert_to_ros_message(msg, *ptr);
      return std::unique_ptr<ROSMessageType, ROSMessageTypeDeleter>(ptr, ros_message_type_deleter_);
    } else {
      static_assert(
        !sizeof(MessageT *),
        "convert_custom_type_to_ros_message_unique_ptr() "
        "unexpectedly called without specialized TypeAdapter");
    }
  }

  // Dispatch when input is a ros message and the output could be anything.
  template<typename TMsg = ROSMessageType>
  typename std::enable_if<!serialization_traits::is_serialized_message_class<TMsg>::value,
    void>::type
  dispatch(
    std::shared_ptr<ROSMessageType> message,
    const rclcpp::MessageInfo & message_info)
  {
    std::unique_lock<std::recursive_mutex> callback_lock(callback_mutex_);
    if (callback_disabled_.load()) {
      return;
    }
    TRACETOOLS_TRACEPOINT(callback_start, static_cast<const void *>(this), false);
    if (!dispatch_ros_) {
      throw std::runtime_error(
              is_serialized_
              ? "cannot dispatch rclcpp::SerializedMessage to non-rclcpp::SerializedMessage callbacks"
              : "dispatch called on an unset AnySubscriptionCallback");
    }
    dispatch_ros_(std::move(message), message_info);
    TRACETOOLS_TRACEPOINT(callback_end, static_cast<const void *>(this));
  }

  // Dispatch when input is a serialized message and the output could be anything.
  void
  dispatch(
    std::shared_ptr<const rclcpp::SerializedMessage> serialized_message,
    const rclcpp::MessageInfo & message_info)
  {
    std::unique_lock<std::recursive_mutex> callback_lock(callback_mutex_);
    if (callback_disabled_.load()) {
      return;
    }
    TRACETOOLS_TRACEPOINT(callback_start, static_cast<const void *>(this), false);
    if (!dispatch_serialized_) {
      throw std::runtime_error(
              (dispatch_ros_ || dispatch_intra_shared_ || dispatch_intra_unique_)
              ? "cannot dispatch rclcpp::SerializedMessage to non-rclcpp::SerializedMessage callbacks"
              : "dispatch called on an unset AnySubscriptionCallback");
    }
    dispatch_serialized_(std::move(serialized_message), message_info);
    TRACETOOLS_TRACEPOINT(callback_end, static_cast<const void *>(this));
  }

  void
  dispatch_intra_process(
    std::shared_ptr<const SubscribedType> message,
    const rclcpp::MessageInfo & message_info)
  {
    std::unique_lock<std::recursive_mutex> callback_lock(callback_mutex_);
    if (callback_disabled_.load()) {
      return;
    }
    TRACETOOLS_TRACEPOINT(callback_start, static_cast<const void *>(this), true);
    if (!dispatch_intra_shared_) {
      throw std::runtime_error(
              is_serialized_
              ? "Cannot dispatch std::shared_ptr<const ROSMessageType> message "
              "to rclcpp::SerializedMessage"
              : "dispatch called on an unset AnySubscriptionCallback");
    }
    dispatch_intra_shared_(std::move(message), message_info);
    TRACETOOLS_TRACEPOINT(callback_end, static_cast<const void *>(this));
  }

  void
  dispatch_intra_process(
    std::unique_ptr<SubscribedType, SubscribedTypeDeleter> message,
    const rclcpp::MessageInfo & message_info)
  {
    std::unique_lock<std::recursive_mutex> callback_lock(callback_mutex_);
    if (callback_disabled_.load()) {
      return;
    }
    TRACETOOLS_TRACEPOINT(callback_start, static_cast<const void *>(this), true);
    if (!dispatch_intra_unique_) {
      throw std::runtime_error(
              is_serialized_
              ? "Cannot dispatch std::unique_ptr<ROSMessageType, ROSMessageTypeDeleter> message "
              "to rclcpp::SerializedMessage"
              : "dispatch called on an unset AnySubscriptionCallback");
    }
    dispatch_intra_unique_(std::move(message), message_info);
    TRACETOOLS_TRACEPOINT(callback_end, static_cast<const void *>(this));
  }

  constexpr
  bool
  use_take_shared_method() const
  {
    return use_take_shared_;
  }

  constexpr
  bool
  is_serialized_message_callback() const
  {
    return is_serialized_;
  }

  void
  register_callback_for_tracing()
  {
    // No-op: tracing registration happens at set() time, where we still have
    // the original typed callback to symbolicate. The dispatch std::functions
    // wrap an adapter lambda whose symbol is uninformative (...::operator()).
  }

private:
  // The 16 (or 30 with TypeAdapter) callback-shape installers. Each one knows
  // how to materialise, for its specific shape, the four dispatch entries: it
  // captures the user's typed callback by value and emits adapter lambdas that
  // convert each of the four dispatch-entry input types into the form the user
  // callback wants. The two routing bools (is_serialized_, use_take_shared_)
  // are set per shape — they used to be implied by the variant alternative's
  // type and are now explicit state.

  // Non-typeadapter / non-serialized shapes (ConstRef / Unique / SharedConstPtr / ConstRefSharedConstPtr,
  // each with and without MessageInfo). For TypeAdapter MessageT the same set of installers also
  // covers the ROSMessage-typed variants of every shape; we discriminate inside.

  // -- ConstRef shapes ------------------------------------------------------
  //
  // The 10 SubscribedType-shaped overloads in this section + UniquePtr/
  // SharedConstPtr/ConstRefSharedConstPtr/SharedPtr below are SFINAE-gated on
  // !is_serialized_message_class<MessageT> because for MessageT=SerializedMessage
  // their std::function signatures collapse onto the *SerializedMessage*
  // overloads (both have SubscribedType==SerializedMessage), creating duplicate
  // declarations. The original variant-based code dropped these alternatives
  // via a 3rd AnySubscriptionCallbackHelper specialization for that case.

  template<typename M = MessageT,
    typename = std::enable_if_t<!serialization_traits::is_serialized_message_class<M>::value>>
  void install_typed_(typename CallbackTypes::ConstRefCallback cb)
  {
    use_take_shared_ = true;
    is_serialized_ = false;
    if constexpr (rclcpp::TypeAdapter<MessageT>::is_specialized::value) {
      dispatch_ros_ = [this, cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo &) {
          auto local = convert_ros_message_to_custom_type_unique_ptr(*m);
          cb(*local);
        };
    } else {
      dispatch_ros_ = [cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo &) {
          cb(*m);
        };
    }
    dispatch_intra_shared_ =
      [cb](std::shared_ptr<const SubscribedType> m, const rclcpp::MessageInfo &) {cb(*m);};
    dispatch_intra_unique_ =
      [cb](std::unique_ptr<SubscribedType, SubscribedTypeDeleter> m, const rclcpp::MessageInfo &) {
        cb(*m);
      };
    dispatch_serialized_ = nullptr;
  }

  template<typename M = MessageT,
    typename = std::enable_if_t<!serialization_traits::is_serialized_message_class<M>::value>>
  void install_typed_(typename CallbackTypes::ConstRefWithInfoCallback cb)
  {
    use_take_shared_ = true;
    is_serialized_ = false;
    if constexpr (rclcpp::TypeAdapter<MessageT>::is_specialized::value) {
      dispatch_ros_ = [this, cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo & i) {
          auto local = convert_ros_message_to_custom_type_unique_ptr(*m);
          cb(*local, i);
        };
    } else {
      dispatch_ros_ = [cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo & i) {
          cb(*m, i);
        };
    }
    dispatch_intra_shared_ =
      [cb](std::shared_ptr<const SubscribedType> m, const rclcpp::MessageInfo & i) {cb(*m, i);};
    dispatch_intra_unique_ =
      [cb](std::unique_ptr<SubscribedType, SubscribedTypeDeleter> m,
        const rclcpp::MessageInfo & i) {
        cb(*m, i);
      };
    dispatch_serialized_ = nullptr;
  }

  // -- ConstRef ROSMessage shapes (only present when TypeAdapter is specialized) ----

  template<bool E = rclcpp::TypeAdapter<MessageT>::is_specialized::value,
    typename = std::enable_if_t<E>>
  void install_typed_(typename CallbackTypes::ConstRefROSMessageCallback cb)
  {
    use_take_shared_ = false;
    is_serialized_ = false;
    dispatch_ros_ = [cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo &) {
        cb(*m);
      };
    dispatch_intra_shared_ =
      [this, cb](std::shared_ptr<const SubscribedType> m, const rclcpp::MessageInfo &) {
        auto local = convert_custom_type_to_ros_message_unique_ptr(*m);
        cb(*local);
      };
    dispatch_intra_unique_ =
      [this, cb](std::unique_ptr<SubscribedType, SubscribedTypeDeleter> m,
        const rclcpp::MessageInfo &) {
        auto local = convert_custom_type_to_ros_message_unique_ptr(*m);
        cb(*local);
      };
    dispatch_serialized_ = nullptr;
  }

  template<bool E = rclcpp::TypeAdapter<MessageT>::is_specialized::value,
    typename = std::enable_if_t<E>>
  void install_typed_(typename CallbackTypes::ConstRefWithInfoROSMessageCallback cb)
  {
    use_take_shared_ = false;
    is_serialized_ = false;
    dispatch_ros_ = [cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo & i) {
        cb(*m, i);
      };
    dispatch_intra_shared_ =
      [this, cb](std::shared_ptr<const SubscribedType> m, const rclcpp::MessageInfo & i) {
        auto local = convert_custom_type_to_ros_message_unique_ptr(*m);
        cb(*local, i);
      };
    dispatch_intra_unique_ =
      [this, cb](std::unique_ptr<SubscribedType, SubscribedTypeDeleter> m,
        const rclcpp::MessageInfo & i) {
        auto local = convert_custom_type_to_ros_message_unique_ptr(*m);
        cb(*local, i);
      };
    dispatch_serialized_ = nullptr;
  }

  // -- UniquePtr shapes -----------------------------------------------------

  template<typename M = MessageT,
    typename = std::enable_if_t<!serialization_traits::is_serialized_message_class<M>::value>>
  void install_typed_(typename CallbackTypes::UniquePtrCallback cb)
  {
    use_take_shared_ = false;
    is_serialized_ = false;
    if constexpr (rclcpp::TypeAdapter<MessageT>::is_specialized::value) {
      dispatch_ros_ = [this, cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo &) {
          cb(convert_ros_message_to_custom_type_unique_ptr(*m));
        };
    } else {
      dispatch_ros_ = [this, cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo &) {
          cb(create_ros_unique_ptr_from_ros_shared_ptr_message(m));
        };
    }
    dispatch_intra_shared_ =
      [this, cb](std::shared_ptr<const SubscribedType> m, const rclcpp::MessageInfo &) {
        cb(create_custom_unique_ptr_from_custom_shared_ptr_message(m));
      };
    dispatch_intra_unique_ =
      [cb](std::unique_ptr<SubscribedType, SubscribedTypeDeleter> m, const rclcpp::MessageInfo &) {
        cb(std::move(m));
      };
    dispatch_serialized_ = nullptr;
  }

  template<typename M = MessageT,
    typename = std::enable_if_t<!serialization_traits::is_serialized_message_class<M>::value>>
  void install_typed_(typename CallbackTypes::UniquePtrWithInfoCallback cb)
  {
    use_take_shared_ = false;
    is_serialized_ = false;
    if constexpr (rclcpp::TypeAdapter<MessageT>::is_specialized::value) {
      dispatch_ros_ = [this, cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo & i) {
          cb(convert_ros_message_to_custom_type_unique_ptr(*m), i);
        };
    } else {
      dispatch_ros_ = [this, cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo & i) {
          cb(create_ros_unique_ptr_from_ros_shared_ptr_message(m), i);
        };
    }
    dispatch_intra_shared_ =
      [this, cb](std::shared_ptr<const SubscribedType> m, const rclcpp::MessageInfo & i) {
        cb(create_custom_unique_ptr_from_custom_shared_ptr_message(m), i);
      };
    dispatch_intra_unique_ =
      [cb](std::unique_ptr<SubscribedType, SubscribedTypeDeleter> m,
        const rclcpp::MessageInfo & i) {
        cb(std::move(m), i);
      };
    dispatch_serialized_ = nullptr;
  }

  // -- UniquePtr ROSMessage shapes -----------------------------------------

  template<bool E = rclcpp::TypeAdapter<MessageT>::is_specialized::value,
    typename = std::enable_if_t<E>>
  void install_typed_(typename CallbackTypes::UniquePtrROSMessageCallback cb)
  {
    use_take_shared_ = false;
    is_serialized_ = false;
    dispatch_ros_ = [this, cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo &) {
        cb(create_ros_unique_ptr_from_ros_shared_ptr_message(m));
      };
    dispatch_intra_shared_ =
      [this, cb](std::shared_ptr<const SubscribedType> m, const rclcpp::MessageInfo &) {
        cb(convert_custom_type_to_ros_message_unique_ptr(*m));
      };
    dispatch_intra_unique_ =
      [this, cb](std::unique_ptr<SubscribedType, SubscribedTypeDeleter> m,
        const rclcpp::MessageInfo &) {
        cb(convert_custom_type_to_ros_message_unique_ptr(*m));
      };
    dispatch_serialized_ = nullptr;
  }

  template<bool E = rclcpp::TypeAdapter<MessageT>::is_specialized::value,
    typename = std::enable_if_t<E>>
  void install_typed_(typename CallbackTypes::UniquePtrWithInfoROSMessageCallback cb)
  {
    use_take_shared_ = false;
    is_serialized_ = false;
    dispatch_ros_ = [this, cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo & i) {
        cb(create_ros_unique_ptr_from_ros_shared_ptr_message(m), i);
      };
    dispatch_intra_shared_ =
      [this, cb](std::shared_ptr<const SubscribedType> m, const rclcpp::MessageInfo & i) {
        cb(convert_custom_type_to_ros_message_unique_ptr(*m), i);
      };
    dispatch_intra_unique_ =
      [this, cb](std::unique_ptr<SubscribedType, SubscribedTypeDeleter> m,
        const rclcpp::MessageInfo & i) {
        cb(convert_custom_type_to_ros_message_unique_ptr(*m), i);
      };
    dispatch_serialized_ = nullptr;
  }

  // -- SharedConstPtr shapes ------------------------------------------------

  template<typename M = MessageT,
    typename = std::enable_if_t<!serialization_traits::is_serialized_message_class<M>::value>>
  void install_typed_(typename CallbackTypes::SharedConstPtrCallback cb)
  {
    use_take_shared_ = true;
    is_serialized_ = false;
    if constexpr (rclcpp::TypeAdapter<MessageT>::is_specialized::value) {
      dispatch_ros_ = [this, cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo &) {
          cb(convert_ros_message_to_custom_type_unique_ptr(*m));
        };
    } else {
      dispatch_ros_ = [cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo &) {
          cb(m);
        };
    }
    dispatch_intra_shared_ =
      [cb](std::shared_ptr<const SubscribedType> m, const rclcpp::MessageInfo &) {cb(m);};
    dispatch_intra_unique_ =
      [cb](std::unique_ptr<SubscribedType, SubscribedTypeDeleter> m, const rclcpp::MessageInfo &) {
        cb(std::move(m));
      };
    dispatch_serialized_ = nullptr;
  }

  template<typename M = MessageT,
    typename = std::enable_if_t<!serialization_traits::is_serialized_message_class<M>::value>>
  void install_typed_(typename CallbackTypes::SharedConstPtrWithInfoCallback cb)
  {
    use_take_shared_ = true;
    is_serialized_ = false;
    if constexpr (rclcpp::TypeAdapter<MessageT>::is_specialized::value) {
      dispatch_ros_ = [this, cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo & i) {
          cb(convert_ros_message_to_custom_type_unique_ptr(*m), i);
        };
    } else {
      dispatch_ros_ = [cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo & i) {
          cb(m, i);
        };
    }
    dispatch_intra_shared_ =
      [cb](std::shared_ptr<const SubscribedType> m, const rclcpp::MessageInfo & i) {cb(m, i);};
    dispatch_intra_unique_ =
      [cb](std::unique_ptr<SubscribedType, SubscribedTypeDeleter> m,
        const rclcpp::MessageInfo & i) {
        cb(std::move(m), i);
      };
    dispatch_serialized_ = nullptr;
  }

  // -- SharedConstPtr ROSMessage shapes ------------------------------------

  template<bool E = rclcpp::TypeAdapter<MessageT>::is_specialized::value,
    typename = std::enable_if_t<E>>
  void install_typed_(typename CallbackTypes::SharedConstPtrROSMessageCallback cb)
  {
    use_take_shared_ = false;
    is_serialized_ = false;
    dispatch_ros_ = [cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo &) {cb(m);};
    dispatch_intra_shared_ =
      [this, cb](std::shared_ptr<const SubscribedType> m, const rclcpp::MessageInfo &) {
        cb(convert_custom_type_to_ros_message_unique_ptr(*m));
      };
    dispatch_intra_unique_ =
      [this, cb](std::unique_ptr<SubscribedType, SubscribedTypeDeleter> m,
        const rclcpp::MessageInfo &) {
        cb(convert_custom_type_to_ros_message_unique_ptr(*m));
      };
    dispatch_serialized_ = nullptr;
  }

  template<bool E = rclcpp::TypeAdapter<MessageT>::is_specialized::value,
    typename = std::enable_if_t<E>>
  void install_typed_(typename CallbackTypes::SharedConstPtrWithInfoROSMessageCallback cb)
  {
    use_take_shared_ = false;
    is_serialized_ = false;
    dispatch_ros_ = [cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo & i) {
        cb(m, i);
      };
    dispatch_intra_shared_ =
      [this, cb](std::shared_ptr<const SubscribedType> m, const rclcpp::MessageInfo & i) {
        cb(convert_custom_type_to_ros_message_unique_ptr(*m), i);
      };
    dispatch_intra_unique_ =
      [this, cb](std::unique_ptr<SubscribedType, SubscribedTypeDeleter> m,
        const rclcpp::MessageInfo & i) {
        cb(convert_custom_type_to_ros_message_unique_ptr(*m), i);
      };
    dispatch_serialized_ = nullptr;
  }

  // -- ConstRefSharedConstPtr shapes (alias same dispatch behaviour as SharedConstPtr) -----

  template<typename M = MessageT,
    typename = std::enable_if_t<!serialization_traits::is_serialized_message_class<M>::value>>
  void install_typed_(typename CallbackTypes::ConstRefSharedConstPtrCallback cb)
  {
    use_take_shared_ = true;
    is_serialized_ = false;
    if constexpr (rclcpp::TypeAdapter<MessageT>::is_specialized::value) {
      dispatch_ros_ = [this, cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo &) {
          cb(convert_ros_message_to_custom_type_unique_ptr(*m));
        };
    } else {
      dispatch_ros_ = [cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo &) {
          cb(m);
        };
    }
    dispatch_intra_shared_ =
      [cb](std::shared_ptr<const SubscribedType> m, const rclcpp::MessageInfo &) {cb(m);};
    dispatch_intra_unique_ =
      [cb](std::unique_ptr<SubscribedType, SubscribedTypeDeleter> m, const rclcpp::MessageInfo &) {
        cb(std::move(m));
      };
    dispatch_serialized_ = nullptr;
  }

  template<typename M = MessageT,
    typename = std::enable_if_t<!serialization_traits::is_serialized_message_class<M>::value>>
  void install_typed_(typename CallbackTypes::ConstRefSharedConstPtrWithInfoCallback cb)
  {
    use_take_shared_ = true;
    is_serialized_ = false;
    if constexpr (rclcpp::TypeAdapter<MessageT>::is_specialized::value) {
      dispatch_ros_ = [this, cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo & i) {
          cb(convert_ros_message_to_custom_type_unique_ptr(*m), i);
        };
    } else {
      dispatch_ros_ = [cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo & i) {
          cb(m, i);
        };
    }
    dispatch_intra_shared_ =
      [cb](std::shared_ptr<const SubscribedType> m, const rclcpp::MessageInfo & i) {cb(m, i);};
    dispatch_intra_unique_ =
      [cb](std::unique_ptr<SubscribedType, SubscribedTypeDeleter> m,
        const rclcpp::MessageInfo & i) {
        cb(std::move(m), i);
      };
    dispatch_serialized_ = nullptr;
  }

  template<bool E = rclcpp::TypeAdapter<MessageT>::is_specialized::value,
    typename = std::enable_if_t<E>>
  void install_typed_(typename CallbackTypes::ConstRefSharedConstPtrROSMessageCallback cb)
  {
    use_take_shared_ = false;
    is_serialized_ = false;
    dispatch_ros_ = [cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo &) {cb(m);};
    dispatch_intra_shared_ =
      [this, cb](std::shared_ptr<const SubscribedType> m, const rclcpp::MessageInfo &) {
        cb(convert_custom_type_to_ros_message_unique_ptr(*m));
      };
    dispatch_intra_unique_ =
      [this, cb](std::unique_ptr<SubscribedType, SubscribedTypeDeleter> m,
        const rclcpp::MessageInfo &) {
        cb(convert_custom_type_to_ros_message_unique_ptr(*m));
      };
    dispatch_serialized_ = nullptr;
  }

  template<bool E = rclcpp::TypeAdapter<MessageT>::is_specialized::value,
    typename = std::enable_if_t<E>>
  void install_typed_(
    typename CallbackTypes::ConstRefSharedConstPtrWithInfoROSMessageCallback cb)
  {
    use_take_shared_ = false;
    is_serialized_ = false;
    dispatch_ros_ = [cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo & i) {
        cb(m, i);
      };
    dispatch_intra_shared_ =
      [this, cb](std::shared_ptr<const SubscribedType> m, const rclcpp::MessageInfo & i) {
        cb(convert_custom_type_to_ros_message_unique_ptr(*m), i);
      };
    dispatch_intra_unique_ =
      [this, cb](std::unique_ptr<SubscribedType, SubscribedTypeDeleter> m,
        const rclcpp::MessageInfo & i) {
        cb(convert_custom_type_to_ros_message_unique_ptr(*m), i);
      };
    dispatch_serialized_ = nullptr;
  }

  // -- Deprecated SharedPtr (non-const) shapes — same routing as SharedConstPtr per current behaviour
  // (in current dispatch they share the same visit-branch).

  template<typename M = MessageT,
    typename = std::enable_if_t<!serialization_traits::is_serialized_message_class<M>::value>>
  void install_typed_(typename CallbackTypes::SharedPtrCallback cb)
  {
    use_take_shared_ = false;
    is_serialized_ = false;
    if constexpr (rclcpp::TypeAdapter<MessageT>::is_specialized::value) {
      dispatch_ros_ = [this, cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo &) {
          cb(convert_ros_message_to_custom_type_unique_ptr(*m));
        };
    } else {
      dispatch_ros_ = [cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo &) {cb(m);};
    }
    dispatch_intra_shared_ = nullptr;  // deprecated shared_ptr<T> shapes only fire on inter-process
    dispatch_intra_unique_ =
      [cb](std::unique_ptr<SubscribedType, SubscribedTypeDeleter> m, const rclcpp::MessageInfo &) {
        cb(std::move(m));
      };
    dispatch_serialized_ = nullptr;
  }

  template<typename M = MessageT,
    typename = std::enable_if_t<!serialization_traits::is_serialized_message_class<M>::value>>
  void install_typed_(typename CallbackTypes::SharedPtrWithInfoCallback cb)
  {
    use_take_shared_ = false;
    is_serialized_ = false;
    if constexpr (rclcpp::TypeAdapter<MessageT>::is_specialized::value) {
      dispatch_ros_ = [this, cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo & i) {
          cb(convert_ros_message_to_custom_type_unique_ptr(*m), i);
        };
    } else {
      dispatch_ros_ = [cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo & i) {
          cb(m, i);
        };
    }
    dispatch_intra_shared_ = nullptr;
    dispatch_intra_unique_ =
      [cb](std::unique_ptr<SubscribedType, SubscribedTypeDeleter> m,
        const rclcpp::MessageInfo & i) {
        cb(std::move(m), i);
      };
    dispatch_serialized_ = nullptr;
  }

  template<bool E = rclcpp::TypeAdapter<MessageT>::is_specialized::value,
    typename = std::enable_if_t<E>>
  void install_typed_(typename CallbackTypes::SharedPtrROSMessageCallback cb)
  {
    use_take_shared_ = false;
    is_serialized_ = false;
    dispatch_ros_ = [cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo &) {cb(m);};
    dispatch_intra_shared_ = nullptr;
    dispatch_intra_unique_ =
      [this, cb](std::unique_ptr<SubscribedType, SubscribedTypeDeleter> m,
        const rclcpp::MessageInfo &) {
        cb(convert_custom_type_to_ros_message_unique_ptr(*m));
      };
    dispatch_serialized_ = nullptr;
  }

  template<bool E = rclcpp::TypeAdapter<MessageT>::is_specialized::value,
    typename = std::enable_if_t<E>>
  void install_typed_(typename CallbackTypes::SharedPtrWithInfoROSMessageCallback cb)
  {
    use_take_shared_ = false;
    is_serialized_ = false;
    dispatch_ros_ = [cb](std::shared_ptr<ROSMessageType> m, const rclcpp::MessageInfo & i) {
        cb(m, i);
      };
    dispatch_intra_shared_ = nullptr;
    dispatch_intra_unique_ =
      [this, cb](std::unique_ptr<SubscribedType, SubscribedTypeDeleter> m,
        const rclcpp::MessageInfo & i) {
        cb(convert_custom_type_to_ros_message_unique_ptr(*m), i);
      };
    dispatch_serialized_ = nullptr;
  }

  // -- Serialized message shapes -------------------------------------------

  void install_typed_(typename CallbackTypes::ConstRefSerializedMessageCallback cb)
  {
    is_serialized_ = true;
    use_take_shared_ = false;
    dispatch_serialized_ =
      [cb](std::shared_ptr<const rclcpp::SerializedMessage> m, const rclcpp::MessageInfo &) {
        cb(*m);
      };
    dispatch_ros_ = nullptr;
    dispatch_intra_shared_ = nullptr;
    dispatch_intra_unique_ = nullptr;
  }

  void install_typed_(typename CallbackTypes::ConstRefSerializedMessageWithInfoCallback cb)
  {
    is_serialized_ = true;
    use_take_shared_ = false;
    dispatch_serialized_ =
      [cb](std::shared_ptr<const rclcpp::SerializedMessage> m, const rclcpp::MessageInfo & i) {
        cb(*m, i);
      };
    dispatch_ros_ = nullptr;
    dispatch_intra_shared_ = nullptr;
    dispatch_intra_unique_ = nullptr;
  }

  void install_typed_(typename CallbackTypes::UniquePtrSerializedMessageCallback cb)
  {
    is_serialized_ = true;
    use_take_shared_ = false;
    dispatch_serialized_ =
      [this, cb](std::shared_ptr<const rclcpp::SerializedMessage> m, const rclcpp::MessageInfo &) {
        cb(create_serialized_message_unique_ptr_from_shared_ptr(m));
      };
    dispatch_ros_ = nullptr;
    dispatch_intra_shared_ = nullptr;
    dispatch_intra_unique_ = nullptr;
  }

  void install_typed_(typename CallbackTypes::UniquePtrSerializedMessageWithInfoCallback cb)
  {
    is_serialized_ = true;
    use_take_shared_ = false;
    dispatch_serialized_ =
      [this, cb](std::shared_ptr<const rclcpp::SerializedMessage> m,
        const rclcpp::MessageInfo & i) {
        cb(create_serialized_message_unique_ptr_from_shared_ptr(m), i);
      };
    dispatch_ros_ = nullptr;
    dispatch_intra_shared_ = nullptr;
    dispatch_intra_unique_ = nullptr;
  }

  // Shared-ptr-to-const serialized shapes — current code dispatches them through the
  // same branch that builds a unique_ptr from the shared (see std::visit body for
  // SharedConstPtr serialized callbacks in the existing dispatch()). Preserve that.
  void install_typed_(typename CallbackTypes::SharedConstPtrSerializedMessageCallback cb)
  {
    is_serialized_ = true;
    use_take_shared_ = false;  // serialized SharedConstPtr is not in the use_take_shared whitelist
    dispatch_serialized_ =
      [this, cb](std::shared_ptr<const rclcpp::SerializedMessage> m, const rclcpp::MessageInfo &) {
        cb(create_serialized_message_unique_ptr_from_shared_ptr(m));
      };
    dispatch_ros_ = nullptr;
    dispatch_intra_shared_ = nullptr;
    dispatch_intra_unique_ = nullptr;
  }

  void install_typed_(typename CallbackTypes::SharedConstPtrSerializedMessageWithInfoCallback cb)
  {
    is_serialized_ = true;
    use_take_shared_ = false;
    dispatch_serialized_ =
      [this, cb](std::shared_ptr<const rclcpp::SerializedMessage> m,
        const rclcpp::MessageInfo & i) {
        cb(create_serialized_message_unique_ptr_from_shared_ptr(m), i);
      };
    dispatch_ros_ = nullptr;
    dispatch_intra_shared_ = nullptr;
    dispatch_intra_unique_ = nullptr;
  }

  void install_typed_(typename CallbackTypes::ConstRefSharedConstPtrSerializedMessageCallback cb)
  {
    is_serialized_ = true;
    use_take_shared_ = false;
    dispatch_serialized_ =
      [this, cb](std::shared_ptr<const rclcpp::SerializedMessage> m, const rclcpp::MessageInfo &) {
        cb(create_serialized_message_unique_ptr_from_shared_ptr(m));
      };
    dispatch_ros_ = nullptr;
    dispatch_intra_shared_ = nullptr;
    dispatch_intra_unique_ = nullptr;
  }

  void install_typed_(
    typename CallbackTypes::ConstRefSharedConstPtrSerializedMessageWithInfoCallback cb)
  {
    is_serialized_ = true;
    use_take_shared_ = false;
    dispatch_serialized_ =
      [this, cb](std::shared_ptr<const rclcpp::SerializedMessage> m,
        const rclcpp::MessageInfo & i) {
        cb(create_serialized_message_unique_ptr_from_shared_ptr(m), i);
      };
    dispatch_ros_ = nullptr;
    dispatch_intra_shared_ = nullptr;
    dispatch_intra_unique_ = nullptr;
  }

  void install_typed_(typename CallbackTypes::SharedPtrSerializedMessageCallback cb)
  {
    is_serialized_ = true;
    use_take_shared_ = false;
    dispatch_serialized_ =
      [this, cb](std::shared_ptr<const rclcpp::SerializedMessage> m, const rclcpp::MessageInfo &) {
        cb(create_serialized_message_unique_ptr_from_shared_ptr(m));
      };
    dispatch_ros_ = nullptr;
    dispatch_intra_shared_ = nullptr;
    dispatch_intra_unique_ = nullptr;
  }

  void install_typed_(typename CallbackTypes::SharedPtrSerializedMessageWithInfoCallback cb)
  {
    is_serialized_ = true;
    use_take_shared_ = false;
    dispatch_serialized_ =
      [this, cb](std::shared_ptr<const rclcpp::SerializedMessage> m,
        const rclcpp::MessageInfo & i) {
        cb(create_serialized_message_unique_ptr_from_shared_ptr(m), i);
      };
    dispatch_ros_ = nullptr;
    dispatch_intra_shared_ = nullptr;
    dispatch_intra_unique_ = nullptr;
  }

  template<typename CallbackT>
  void register_callback_for_tracing_(const CallbackT & callback)
  {
#ifndef TRACETOOLS_DISABLED
    if (TRACETOOLS_TRACEPOINT_ENABLED(rclcpp_callback_register)) {
      char * symbol = tracetools::get_symbol(callback);
      TRACETOOLS_DO_TRACEPOINT(
        rclcpp_callback_register,
        static_cast<const void *>(this),
        symbol);
      std::free(symbol);
    }
#else
    (void)callback;
#endif  // TRACETOOLS_DISABLED
  }

  RosDispatchFn dispatch_ros_;
  SerializedDispatchFn dispatch_serialized_;
  IntraSharedDispatchFn dispatch_intra_shared_;
  IntraUniqueDispatchFn dispatch_intra_unique_;

  // Routing flags. Used to live as a side-effect of the variant alternative's
  // type; now explicit state set per install_typed_ overload.
  bool is_serialized_ = false;
  bool use_take_shared_ = false;

  std::recursive_mutex callback_mutex_;
  std::atomic_bool callback_disabled_{false};

  SubscribedTypeAllocator subscribed_type_allocator_;
  SubscribedTypeDeleter subscribed_type_deleter_;
  ROSMessageTypeAllocator ros_message_type_allocator_;
  ROSMessageTypeDeleter ros_message_type_deleter_;
  SerializedMessageAllocator serialized_message_allocator_;
  SerializedMessageDeleter serialized_message_deleter_;
};

}  // namespace rclcpp

#endif  // RCLCPP__ANY_SUBSCRIPTION_CALLBACK_HPP_
