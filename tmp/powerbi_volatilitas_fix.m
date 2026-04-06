// ══════════════════════════════════════════════════════════════════
// FIX 1: (Data)Indeks Volatilitas
// Ganti SharePoint (Data)Makro.xlsx → Azure SQL data_volatility_index
// Output columns sama: Date (date), Indeks Volatilitas (VIX) (number)
// ══════════════════════════════════════════════════════════════════
let
    Source = Sql.Database("pei-dashboard.database.windows.net", "pei-dashboard",
        [HierarchicalNavigation=true, MultiSubnetFailover=true]),
    dbo = Source{[Schema="dbo"]}[Data],
    data_volatility_index = dbo{[Name="data_volatility_index"]}[Data],

    SelectedCols = Table.SelectColumns(data_volatility_index,
        {"indicator_date", "index_value"}),

    RenamedCols = Table.RenameColumns(SelectedCols, {
        {"indicator_date", "Date"},
        {"index_value", "Last Price"}
    }),

    #"Changed Type" = Table.TransformColumnTypes(RenamedCols, {
        {"Date", type date},
        {"Last Price", type number}
    }),

    #"Renamed Columns" = Table.RenameColumns(#"Changed Type", {
        {"Last Price", "Indeks Volatilitas (VIX)"}
    })
in
    #"Renamed Columns"


// ══════════════════════════════════════════════════════════════════
// FIX 2: (News)indeks volatilitas
// Ganti SharePoint (News)Scrapping.xlsx → Azure SQL news_articles
// Output columns sama: title, date, url, content, source, keyword + Berita Pilihan
// FIX: date dari SQL Server bertipe datetime2 → harus convert ke type date
//      sebelum Text.From() agar format "1/1/2025" bukan "1/1/2025 12:00:00 AM"
// ══════════════════════════════════════════════════════════════════
let
    Source = Sql.Database("pei-dashboard.database.windows.net", "pei-dashboard",
        [HierarchicalNavigation=true, MultiSubnetFailover=true]),
    dbo = Source{[Schema="dbo"]}[Data],
    news_articles = dbo{[Name="news_articles"]}[Data],
    news_sources = dbo{[Name="news_sources"]}[Data],

    FilteredArticles = Table.SelectRows(news_articles,
        each [category] = "indeks volatilitas"),

    // Join dengan news_sources untuk ambil source name
    JoinedTables = Table.NestedJoin(FilteredArticles, {"source_id"}, news_sources, {"id"}, "ns", JoinKind.LeftOuter),
    ExpandedSource = Table.ExpandTableColumn(JoinedTables, "ns", {"name"}, {"source"}),

    // Pilih dan rename kolom agar sama dengan SharePoint
    SelectedCols = Table.SelectColumns(ExpandedSource, {
        "title", "published_date", "url", "content", "source", "category"
    }),

    RenamedCols = Table.RenameColumns(SelectedCols, {
        {"published_date", "date"},
        {"category", "keyword"}
    }),

    // FIX: convert ke type date sebelum Text.From()
    #"Changed Type" = Table.TransformColumnTypes(RenamedCols, {
        {"title", type any},
        {"date", type date},
        {"url", type any},
        {"content", type any},
        {"source", type any},
        {"keyword", type any}
    }),

    #"Added Custom" = Table.AddColumn(#"Changed Type", "Berita Pilihan",
        each "[" & Text.From([date]) & "] " & [title] & " - " & [source])
in
    #"Added Custom"


// ══════════════════════════════════════════════════════════════════
// FIX 3: (Summary)Idx Volatilitas
// Ganti SharePoint (News)Sentiment.xlsx → Azure SQL sentiment_analyses
// Output columns sama: Tanggal awal, Tanggal akhir, Summary, Summary Data, Rentang_IdxVolatilitas
// FIX: date dari SQL Server bertipe datetime2 → convert via Int64 tidak bisa,
//      langsung convert ke type date saja
// ══════════════════════════════════════════════════════════════════
let
    Source = Sql.Database("pei-dashboard.database.windows.net", "pei-dashboard",
        [HierarchicalNavigation=true, MultiSubnetFailover=true]),
    dbo = Source{[Schema="dbo"]}[Data],
    sentiment_analyses = dbo{[Name="sentiment_analyses"]}[Data],

    FilteredRows = Table.SelectRows(sentiment_analyses,
        each [role_context] = "Idx Volatilitas"),

    SelectedCols = Table.SelectColumns(FilteredRows, {
        "date_range_start", "date_range_end", "summary", "summary_data"
    }),

    // Rename agar sama persis dengan kolom SharePoint
    RenamedCols = Table.RenameColumns(SelectedCols, {
        {"date_range_start", "Tanggal awal"},
        {"date_range_end",   "Tanggal akhir"},
        {"summary",          "Summary"},
        {"summary_data",     "Summary Data"}
    }),

    // FIX: dari SQL Server langsung convert ke type date (skip Int64 step)
    #"Changed Type" = Table.TransformColumnTypes(RenamedCols, {
        {"Summary",      type text},
        {"Summary Data", type text}
    }),

    #"Changed Type1" = Table.TransformColumnTypes(#"Changed Type", {
        {"Tanggal awal",  type date},
        {"Tanggal akhir", type date}
    }),

    #"Added Custom" = Table.AddColumn(#"Changed Type1", "Rentang_IdxVolatilitas",
        each Text.From([Tanggal awal]) & " : " & Text.From([Tanggal akhir]))
in
    #"Added Custom"
