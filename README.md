[![test.ai sdk logo](https://testdotai.github.io/static-assets/shared/logo-sdk.png)](https://test.ai/sdk)

[![Python 3.7+](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org)
[![Apache 2.0](https://img.shields.io/badge/Apache-2.0-blue)](https://www.apache.org/licenses/LICENSE-2.0)
[![PyPI](https://img.shields.io/pypi/v/test-ai-selenium)](https://pypi.org/project/test-ai-selenium/)
[![Discord](https://img.shields.io/discord/853669216880295946?&logo=discord)](https://sdk.test.ai/discord)

The test.ai selenium SDK is a simple library that makes it easy to write robust cross-browser web tests backed by computer vision and artificial intelligence.

test.ai integrates seamelessly with your existing tests, and will act as backup if your selectors break/fail by attempting to visually (computer vision) identify elements.

The test.ai SDK is able to accomplish this by automatically ingesting your selenium elements (using both screenshots and element names) when you run your test cases with test.ai for the first time. 

The SDK is accompanied by a [web-based editor](https://sdk.test.ai/) which makes building visual test cases easy; you can draw boxes around your elements instead of using fragile CSS or XPath selectors.

## Install
In your terminal, run

```bash
pip install test-ai-selenium
```
## Tutorial
We have a detailed step-by-step tutorial which will help you get set up with the SDK: https://github.com/testdotai/python-selenium-sdk-demo

## Resources
* [Register/Login to your test.ai account](https://sdk.test.ai/login)
* [API Docs](https://test.ai/sdk) <!-- TODO: FIXME -->
* [Another Tutorial](https://sdk.test.ai/tutorial)