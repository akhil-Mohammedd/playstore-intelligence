# Data dictionary

Source app columns: App, Category, Rating, Reviews, Size, Installs, Type, Price, Content Rating, Genres, Last Updated, Current Ver, Android Ver. Optional review CSV includes App, Translated_Review, Sentiment, Sentiment_Polarity, Sentiment_Subjectivity.

| Processed field | Meaning |
|---|---|
| `app`, `category`, `genres` | Trimmed source strings; original values retained in normalized columns |
| `rating` | Numeric source rating, outside [1,5] set missing; missing is not zero |
| `reviews` | Numeric count parsed after removing thousands separators |
| `installs_raw` | Original source install band |
| `estimated_installs_lower_bound` | Numeric lower bound from install band; not exact installs |
| `price_raw`, `price_usd` | Original source price and parsed numeric price |
| `size_raw`, `size_mb` | Original size and size converted to MB; variable/unparseable size missing |
| `last_updated_raw`, `last_updated` | Original source date text and parsed date; not release date |
| `type` | Trimmed source type, normalized Free/Paid capitalization |
| `category_valid` | Whether category follows observed uppercase/underscore source convention |
| `exact_duplicate` | Exact repeat of an earlier source row; retained in output |
| `analysis_eligible` | False for exact repeats or malformed category rows; used to avoid duplicate/category corruption in summaries |

The source schema is documented above; all raw files remain immutable in KaggleHub cache.
