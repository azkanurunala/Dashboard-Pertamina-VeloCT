// ══════════════════════════════════════════════════════
// (News)SAF — Azure SQL version
// Fix: convert published_date (datetime2) to type date
//      BEFORE Text.From() in "Berita Pilihan"
// ══════════════════════════════════════════════════════
let
    Source = Sql.Database("pei-dashboard.database.windows.net", "pei-dashboard",
        [HierarchicalNavigation=true, MultiSubnetFailover=true]),
    dbo = Source{[Schema="dbo"]}[Data],
    news_articles1   = dbo{[Name="news_articles"]}[Data],
    news_sources1    = dbo{[Name="news_sources"]}[Data],

    // Filter SAF articles
    FilteredRows = Table.SelectRows(news_articles1, each [category] = "SAF"),

    SelectedArticles = Table.SelectColumns(FilteredRows, {
        "title", "published_date", "url", "content", "source_id", "category"
    }),

    // Convert datetime2 → date BEFORE joining / before Text.From()
    ConvertDateType = Table.TransformColumnTypes(SelectedArticles, {
        {"published_date", type date}
    }),

    // Join with news_sources to get source name
    JoinedTables = Table.NestedJoin(ConvertDateType, {"source_id"},
        news_sources1, {"id"}, "SourceTable", JoinKind.LeftOuter),
    ExpandedSource = Table.ExpandTableColumn(JoinedTables, "SourceTable",
        {"name"}, {"source"}),

    // Rename to match SharePoint column names
    RenamedColumns = Table.RenameColumns(ExpandedSource, {
        {"published_date", "date"},
        {"category", "keyword"}
    }),

    SelectedColumns = Table.SelectColumns(RenamedColumns, {
        "title", "date", "url", "content", "source", "keyword"
    }),

    // Berita Pilihan — date is already type date, Text.From gives locale format
    AddBeritaPilihan = Table.AddColumn(SelectedColumns, "Berita Pilihan",
        each "[" & Text.From([date]) & "] " & [title] & " - " & [source]),

    ChangedType = Table.TransformColumnTypes(AddBeritaPilihan, {
        {"title", type text},
        {"url", type text},
        {"content", type text},
        {"source", type text},
        {"keyword", type text},
        {"Berita Pilihan", type text}
    })
in
    ChangedType


// ══════════════════════════════════════════════════════
// (Summary)SAF — Azure SQL version
// Fix: convert date_range_start/end (datetime2) to type date
//      BEFORE Text.From() in "Rentang_SAF"
// Note: verify role_context value matches what is stored in DB
//       (check: SELECT DISTINCT role_context FROM sentiment_analyses)
// ══════════════════════════════════════════════════════
let
    Source = Sql.Database("pei-dashboard.database.windows.net", "pei-dashboard",
        [HierarchicalNavigation=true, MultiSubnetFailover=true]),
    dbo = Source{[Schema="dbo"]}[Data],
    sentiment_analyses1 = dbo{[Name="sentiment_analyses"]}[Data],

    // Filter SAF summaries — role_context must match exactly what is in DB
    FilteredRows = Table.SelectRows(sentiment_analyses1, each [role_context] = "SAF"),

    SelectedColumns = Table.SelectColumns(FilteredRows, {
        "date_range_start", "date_range_end", "summary", "summary_data"
    }),

    // Convert datetime2 → date BEFORE Text.From() in Rentang_SAF
    ConvertDateEarly = Table.TransformColumnTypes(SelectedColumns, {
        {"date_range_start", type date},
        {"date_range_end", type date}
    }),

    // Rename to match SharePoint column names
    RenamedColumns = Table.RenameColumns(ConvertDateEarly, {
        {"date_range_start", "Tanggal awal"},
        {"date_range_end", "Tanggal akhir"},
        {"summary", "Summary"},
        {"summary_data", "Summary Data"}
    }),

    // Rentang_SAF — dates already type date, same as SharePoint
    AddRentang = Table.AddColumn(RenamedColumns, "Rentang_SAF",
        each Text.From([Tanggal awal]) & " : " & Text.From([Tanggal akhir])),

    ChangedType = Table.TransformColumnTypes(AddRentang, {
        {"Summary", type text},
        {"Summary Data", type text},
        {"Rentang_SAF", type text}
    })
in
    ChangedType
