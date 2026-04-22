# The Shrinkflation Detective

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg) ![Database](https://img.shields.io/badge/Database-PostgreSQL-informational.svg) ![Status](https://img.shields.io/badge/Status-Phase_3_In_Progress-yellow.svg) ![Data](https://img.shields.io/badge/Data-Kroger_API_+_FRED-green.svg)

**[Read in English](#english-version) | [Đọc bằng Tiếng Việt](#vietnamese-version)**

---
<a name="english-version" id="english-version"></a>

## English Version

### The Observation

A bowl of crispy stir-fried noodles in Ho Chi Minh City used to cost 55,000 VND and came loaded with shrimp and squid. Today, the same bowl costs 70,000 VND, and the seafood has noticeably thinned out. The nominal price increased 27 percent, but the real price increase was steeper still because the portion shrank at the same time.

This pattern is not unique to Vietnamese street food. In the United States, a bag of Doritos slipped from 9.75 oz to 9.25 oz without a price change. Tropicana orange juice dropped from 64 fl oz to 52 fl oz. Charmin reduced its "double roll" sheet count. In each case, the manufacturer raised the effective price without touching the number on the shelf tag. The Consumer Price Index (CPI), which measures inflation through changes in listed prices, recorded nothing.

Shrinkflation is the name for this practice: reducing product quantity while holding or raising the nominal price. It is a well-documented phenomenon in the economics literature, but it has never been tracked systematically and in real time at scale. This project builds the system to do that.

### What This System Measures

The CPI measures price changes. It does not measure the parallel channel where quantity decreases at a constant price. The two channels together determine what a consumer actually pays per unit of product, yet only one of them is in the official inflation figures.

This project tracks the second channel. For every product SKU in the database, the system records price and normalized weight at weekly intervals. When a product's price per gram or price per milliliter increases without a corresponding change in the listed price, that event is flagged as a shrinkflation occurrence. These events are aggregated by category and by month into a Shrinkflation Index (SFI), a composite indicator that runs alongside the CPI and measures what the CPI leaves out.

This is the second project in a hidden inflation research series. The first, the Shadow Rent Index, was built on the premise that CPI shelter costs structurally lag real rental market prices by 6 to 9 months, a delay that arises from the BLS methodology of sampling existing leases rather than new listings. Shrinkflation is the product dimension of the same broader problem: official statistics miss forms of inflation that do not appear as nominal price changes.

### System Architecture

```
Kroger API --> Python Crawler --> Raw JSON Storage
     |
     v
Regex Unit Normalizer --> price_per_gram / price_per_ml
     |
     v
PostgreSQL (Neon.tech) --> products + snapshots tables
     |
     v
SQL Window Functions (LAG / LEAD) --> shrinkflation detection
     |
     v
Shrinkflation Index (SFI) <--> FRED PPI Correlation
     |
     v
Streamlit Dashboard
```

**Extract:** A Python crawler authenticates against the Kroger Developer API and retrieves product listings across five consumer categories (snacks, dairy, beverages, household goods, personal care), targeting 500 to 1,000 unique SKUs per crawl cycle. Raw JSON responses are written to disk before any parsing occurs.

**Transform:** A regex-based normalization engine parses free-text weight and volume strings from product titles. All solid goods are converted to grams and all liquid goods to milliliters, producing a single comparable unit across every SKU and every time period.

**Load:** Records are inserted into a PostgreSQL database on Neon.tech. The schema deliberately separates product identity (the `products` table) from time-varying observations (the `snapshots` table). This structure enables the `LAG()` and `LEAD()` window functions that power the detection algorithm.

**Analyze:** A macro correlation layer pulls the Producer Price Index (PPI) and CPI from the FRED API and aligns them with the monthly SFI. A Streamlit dashboard with four tabs serves the results: overall SFI over time, category breakdown, individual product lookup, and the PPI correlation view.

GitHub Actions runs the crawl on a weekly cron schedule. Every run appends new snapshot rows without overwriting prior records, which is what makes longitudinal comparison possible.

### Research Questions

The analysis is structured around two falsifiable hypotheses drawn from industrial economics:

**Hypothesis 1 — PPI as a Leading Indicator**

Input cost increases, as measured by the Producer Price Index, lead shrinkflation events by two to three quarters. The proposed mechanism: manufacturers face the same margin pressure as any firm when raw material costs rise, but explicit price increases risk losing price-sensitive customers and triggering retailer pushback. Quietly reducing the package weight is the lower-resistance adjustment. If this channel exists, a cross-correlation between PPI and SFI should show a statistically significant peak at a lag of two to three months.

**Hypothesis 2 — Price Salience as a Predictor of Shrinkflation Rate**

Products in categories where consumers have a strong price reference, such as bread, bottled water, and snack foods, should experience higher shrinkflation rates than products in categories where consumers are less price-aware. The underlying logic is the same: the firmer the consumer's mental anchor on what a product "should" cost, the more a firm will prefer quantity reduction over a visible price increase.

### Project Status

| Phase | Timeline | Description | Status |
|-------|----------|-------------|--------|
| 1. Foundation | Week 1-2 | Database schema, Kroger API setup, first crawl batch | Complete |
| 2. ETL Core | Week 3-4 | Regex unit normalization pipeline, weekly automation | Complete |
| 3. Analytics | Week 5-6 | Shrinkflation Index v1, detection algorithm | In Progress |
| 4. Macro Layer | Week 7-8 | FRED integration, hypothesis testing | Pending |
| 5. Deploy | Week 9-10 | Streamlit dashboard live, case study writeup | Pending |

### Tech Stack

* **Languages:** Python, SQL
* **Data Extraction:** Kroger Developer API, requests
* **Data Transformation:** Pandas, Regular Expressions (Regex)
* **Database:** PostgreSQL, SQLAlchemy, psycopg2, Neon.tech
* **Macro Data:** FRED API (fredapi)
* **Statistical Analysis:** statsmodels (cross-correlation, lag analysis)
* **Visualization:** Streamlit, Plotly Express
* **Automation:** GitHub Actions (weekly cron)

---
<a name="vietnamese-version" id="vietnamese-version"></a>

## Phiên bản Tiếng Việt

### Quan sát ban đầu

Một tô mì xào giòn ở Thành phố Hồ Chí Minh ngày trước có giá 55.000 đồng, đầy tôm mực. Bây giờ cùng tô đó giá lên 70.000 đồng, nhưng tôm mực thì vơi đi rõ rệt. Giá danh nghĩa tăng 27%, nhưng giá thực tế tăng còn nhiều hơn vì khẩu phần cũng bị cắt bớt cùng lúc.

Hiện tượng này không chỉ xảy ra với quán ăn vỉa hè Việt Nam. Tại Mỹ, một túi Doritos lặng lẽ giảm từ 276g xuống còn 262g mà giá không đổi. Nước cam Tropicana giảm từ 1,89 lít xuống còn 1,54 lít. Giấy vệ sinh Charmin cắt bớt số tờ trên mỗi cuộn. Trong từng trường hợp đó, nhà sản xuất đã tăng giá thực sự mà không cần chạm tay vào con số trên nhãn giá. Chỉ số giá tiêu dùng (CPI), vốn chỉ đo lạm phát qua giá niêm yết, không ghi nhận được gì cả.

Shrinkflation là tên gọi cho cách làm này: giảm khối lượng sản phẩm trong khi giá danh nghĩa giữ nguyên hoặc tăng lên. Hiện tượng này đã được ghi nhận trong tài liệu kinh tế học, nhưng chưa từng có hệ thống nào theo dõi nó một cách hệ thống và theo thời gian thực ở quy mô lớn. Dự án này xây dựng hệ thống đó.

### Phương pháp Đo lường

CPI đo sự thay đổi giá niêm yết. Nó không đo kênh song song: khối lượng sản phẩm giảm trong khi giá không đổi. Hai kênh này cộng lại mới xác định được người tiêu dùng thực sự trả bao nhiêu tiền cho mỗi đơn vị sản phẩm, nhưng chỉ có một kênh xuất hiện trong số liệu lạm phát chính thức.

Dự án này theo dõi kênh còn lại. Với mỗi SKU sản phẩm trong cơ sở dữ liệu, hệ thống ghi lại giá và khối lượng chuẩn hóa theo từng tuần. Khi giá trên mỗi gram hoặc giá trên mỗi mililit của một sản phẩm tăng lên mà giá niêm yết không thay đổi, sự kiện đó được đánh dấu là một trường hợp shrinkflation. Các sự kiện này được tổng hợp theo danh mục và theo tháng thành Chỉ số Shrinkflation (SFI), một chỉ báo tổng hợp chạy song song với CPI và đo lường phần mà CPI bỏ qua.

Đây là dự án thứ hai trong chuỗi nghiên cứu lạm phát ẩn. Dự án đầu tiên, Shadow Rent Index, được xây dựng trên tiền đề rằng chi phí nhà ở trong CPI trễ hơn giá thuê thực tế từ 6 đến 9 tháng, một độ trễ xuất phát từ phương pháp luận của BLS khi lấy mẫu từ hợp đồng thuê hiện tại thay vì hợp đồng mới. Shrinkflation là chiều kích sản phẩm của cùng một vấn đề rộng hơn: số liệu chính thức bỏ qua các dạng lạm phát không xuất hiện dưới dạng thay đổi giá danh nghĩa.

### Kiến trúc Hệ thống

```
Kroger API --> Crawler Python --> Lưu JSON thô
     |
     v
Regex Chuẩn hóa Đơn vị --> giá_trên_gram / giá_trên_ml
     |
     v
PostgreSQL (Neon.tech) --> bảng products + snapshots
     |
     v
SQL Window Functions (LAG / LEAD) --> phát hiện shrinkflation
     |
     v
Chỉ số Shrinkflation (SFI) <--> Tương quan PPI từ FRED
     |
     v
Dashboard Streamlit
```

**Trích xuất:** Crawler Python xác thực với Kroger Developer API và truy xuất danh sách sản phẩm trên năm danh mục tiêu dùng (đồ ăn vặt, sữa, đồ uống, gia dụng, chăm sóc cá nhân), hướng đến 500 đến 1.000 SKU duy nhất mỗi chu kỳ. Phản hồi JSON thô được lưu xuống đĩa trước khi bất kỳ bước phân tích nào diễn ra.

**Biến đổi:** Bộ máy chuẩn hóa dựa trên regex phân tích chuỗi trọng lượng và thể tích dạng văn bản tự do từ tiêu đề sản phẩm. Tất cả hàng rắn được chuyển về gram, tất cả hàng lỏng về mililit, tạo ra một đơn vị so sánh thống nhất trên toàn bộ SKU và theo thời gian.

**Tải dữ liệu:** Bản ghi được chèn vào PostgreSQL trên Neon.tech. Schema tách biệt thông tin nhận dạng sản phẩm (bảng `products`) khỏi các quan sát thay đổi theo thời gian (bảng `snapshots`). Cấu trúc này cho phép dùng window function `LAG()` và `LEAD()` để so sánh các snapshot liên tiếp nhằm phát hiện thay đổi kích thước.

**Phân tích:** Tầng tương quan vĩ mô kéo dữ liệu Chỉ số Giá Sản xuất (PPI) và CPI từ FRED API, căn chỉnh với SFI theo tháng. Dashboard Streamlit bốn tab phục vụ kết quả: xu hướng SFI tổng thể, phân tích theo danh mục, tra cứu sản phẩm đơn lẻ, và biểu đồ tương quan PPI.

GitHub Actions chạy toàn bộ pipeline crawl theo lịch cron hàng tuần. Mỗi lần chạy ghi thêm hàng snapshot mới mà không ghi đè dữ liệu cũ, đây là điều kiện cần để so sánh theo chiều dọc thời gian.

### Câu hỏi Nghiên cứu

Phân tích được xây dựng quanh hai giả thuyết có thể bác bỏ được, xuất phát từ kinh tế học công nghiệp:

**Giả thuyết 1 — PPI là chỉ báo sớm**

Chi phí đầu vào tăng, đo bằng Chỉ số Giá Sản xuất (PPI), dẫn trước các sự kiện shrinkflation từ hai đến ba quý. Cơ chế đề xuất: khi chi phí nguyên vật liệu tăng, các nhà sản xuất phải chịu cùng áp lực biên lợi nhuận như bất kỳ doanh nghiệp nào, nhưng tăng giá công khai đồng nghĩa với mất khách hàng nhạy cảm giá và vấp phải sự kháng cự từ nhà bán lẻ. Giảm khẩu phần lặng lẽ là lối thoát ít kháng cự hơn. Nếu kênh truyền dẫn này tồn tại, tương quan chéo giữa PPI và SFI sẽ cho thấy đỉnh có ý nghĩa thống kê tại độ trễ hai đến ba tháng.

**Giả thuyết 2 — Độ nhớ giá như một yếu tố dự báo**

Các sản phẩm trong danh mục mà người tiêu dùng có giá tham chiếu rõ trong đầu, như bánh mì, nước đóng chai và đồ ăn vặt, sẽ có tỷ lệ shrinkflation cao hơn các danh mục mà giá của chúng ít ai nhớ. Logic nền tảng giống nhau: giá neo trong đầu người mua càng chắc, thì doanh nghiệp càng ưu tiên giảm khối lượng hơn là tăng giá niêm yết để tránh phản ứng tiêu cực.

### Trạng thái Dự án

| Giai đoạn | Thời gian | Mô tả | Trạng thái |
|-----------|-----------|-------|------------|
| 1. Nền tảng | Tuần 1-2 | Schema cơ sở dữ liệu, kết nối Kroger API, crawl batch đầu tiên | Hoàn thành |
| 2. ETL Core | Tuần 3-4 | Pipeline chuẩn hóa đơn vị, tự động hóa hàng tuần | Hoàn thành |
| 3. Phân tích | Tuần 5-6 | Chỉ số Shrinkflation v1, thuật toán phát hiện | Đang thực hiện |
| 4. Vĩ mô | Tuần 7-8 | Tích hợp FRED, kiểm định giả thuyết | Chưa bắt đầu |
| 5. Deploy | Tuần 9-10 | Dashboard Streamlit live, viết case study | Chưa bắt đầu |

### Công nghệ

* **Ngôn ngữ:** Python, SQL
* **Thu thập dữ liệu:** Kroger Developer API, requests
* **Xử lý dữ liệu:** Pandas, Biểu thức chính quy (Regex)
* **Cơ sở dữ liệu:** PostgreSQL, SQLAlchemy, psycopg2, Neon.tech
* **Dữ liệu vĩ mô:** FRED API (fredapi)
* **Phân tích thống kê:** statsmodels (tương quan chéo, phân tích độ trễ)
* **Trực quan hóa:** Streamlit, Plotly Express
* **Tự động hóa:** GitHub Actions (cron hàng tuần)

---
*Last update: April 22, 2026*
