#ifndef VDEVICE_NOOP_EXCEPTION_HPP
#define VDEVICE_NOOP_EXCEPTION_HPP

#include <exception>
#include <string>

#include "ccec/Exception.hpp"

namespace device {

class Exception : public std::exception {
public:
    Exception(int code = 0, const std::string& message = "device exception")
        : _code(code)
        , _message(message)
    {
    }

    int getCode() const noexcept
    {
        return _code;
    }

    const char* what() const noexcept override
    {
        return _message.c_str();
    }

private:
    int _code;
    std::string _message;
};

} // namespace device

#endif
