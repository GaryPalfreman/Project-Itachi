import unittest
from unittest.mock import AsyncMock, patch

from app import rapidapi_tools, runtime_health


class RapidApiToolsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        rapidapi_tools._CACHE.clear()
        runtime_health.reset()

    async def test_finance_lookup_resolves_symbol_then_quote(self):
        search = {"bestMatches": [{"1. symbol": "MSFT", "2. name": "Microsoft Corporation",
                                   "4. region": "United States", "8. currency": "USD"}]}
        quote = {"Global Quote": {"05. price": "500.00", "02. open": "490.00",
                                  "03. high": "505.00", "04. low": "488.00",
                                  "06. volume": "1234", "07. latest trading day": "2026-09-25",
                                  "09. change": "10.00", "10. change percent": "2.04%"}}
        with patch.object(rapidapi_tools, "_get_json", new=AsyncMock(side_effect=[search, quote])):
            result = await rapidapi_tools.finance_lookup("Microsoft", "key")
        self.assertIn("MSFT", result)
        self.assertIn("500.00", result)
        self.assertNotIn("Alpha Vantage", result)
        self.assertNotIn("rapidapi.com", result)

    async def test_ticker_query_skips_symbol_search(self):
        quote = {"Global Quote": {"05. price": "500.00", "02. open": "490.00",
                                  "03. high": "505.00", "04. low": "488.00",
                                  "06. volume": "1234", "07. latest trading day": "2026-09-25",
                                  "09. change": "10.00", "10. change percent": "2.04%"}}
        with patch.object(
            rapidapi_tools,
            "_get_json",
            new=AsyncMock(return_value=quote),
        ) as get_json:
            result = await rapidapi_tools.finance_lookup("MSFT", "key")
        self.assertIn("MSFT", result)
        self.assertEqual(get_json.await_count, 1)

    async def test_finance_provider_information_is_failure_not_fake_quote(self):
        payload = {"Information": "rate limit reached"}
        with patch.object(
            rapidapi_tools,
            "_get_json",
            new=AsyncMock(return_value=payload),
        ):
            with self.assertRaises(RuntimeError):
                await rapidapi_tools.finance_lookup("MSFT", "key")

    async def test_city_lookup_formats_candidates(self):
        payload = {"data": [{"city": "Melbourne", "region": "Victoria", "country": "Australia",
                             "countryCode": "AU", "population": 5000000,
                             "latitude": -37.81, "longitude": 144.96}]}
        with patch.object(rapidapi_tools, "_get_json", new=AsyncMock(return_value=payload)):
            result = await rapidapi_tools.city_lookup("Melbourne", "key")
        self.assertIn("Melbourne", result)
        self.assertIn("Australia", result)
        self.assertNotIn("GeoDB", result)
        self.assertNotIn("rapidapi.com", result)

    async def test_word_lookup_formats_lexical_data(self):
        payload = {"results": [{"definition": "a test definition", "partOfSpeech": "noun",
                                "synonyms": ["trial", "check"]}],
                   "pronunciation": {"all": "test"}}
        with patch.object(rapidapi_tools, "_get_json", new=AsyncMock(return_value=payload)):
            result = await rapidapi_tools.word_lookup("test", "key")
        self.assertIn("test definition", result)
        self.assertIn("trial", result)
        self.assertNotIn("WordsAPI", result)
        self.assertNotIn("rapidapi.com", result)

    async def test_search_normalizes_results(self):
        payload = {"data": [{"title": "Example", "url": "https://example.com", "snippet": "Text"}]}
        with patch.object(rapidapi_tools, "_get_json", new=AsyncMock(return_value=payload)):
            result = await rapidapi_tools.web_search("example", "key")
        self.assertEqual(result[0]["url"], "https://example.com")

    async def test_run_tool_rejects_unknown_api(self):
        with self.assertRaises(ValueError):
            await rapidapi_tools.run_tool("arbitrary_proxy", "x", "key")


if __name__ == "__main__":
    unittest.main()
