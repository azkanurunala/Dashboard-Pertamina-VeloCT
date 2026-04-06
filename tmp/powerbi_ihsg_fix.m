let
    Source = Sql.Database("pei-dashboard.database.windows.net", "pei-dashboard", [HierarchicalNavigation=true, MultiSubnetFailover=true]),
    dbo = Source{[Schema="dbo"]}[Data],
    news_articles = dbo{[Name="news_articles"]}[Data],
    news_sources = dbo{[Name="news_sources"]}[Data],

    FilteredArticles = Table.SelectRows(news_articles, each [category] = "IHSG"),

    RenamedArticles = Table.RenameColumns(FilteredArticles, {
        {"title", "title"},
        {"published_date", "date"},
        {"url", "url"},
        {"content", "content"},
        {"category", "keyword"}
    }),

    SelectedArticles = Table.SelectColumns(RenamedArticles, {
        "title", "date", "url", "content", "source_id", "keyword"
    }),

    // ── FIX: convert date to type date SEBELUM AddBeritaPilihan ──
    ConvertDateType = Table.TransformColumnTypes(SelectedArticles, {
        {"date", type date}
    }),

    RenamedSources = Table.RenameColumns(news_sources, {
        {"id", "source_id"},
        {"name", "source"}
    }),

    SelectedSources = Table.SelectColumns(RenamedSources, {
        "source_id", "source"
    }),

    JoinedTables = Table.NestedJoin(ConvertDateType, {"source_id"}, SelectedSources, {"source_id"}, "news_sources", JoinKind.LeftOuter),

    ExpandedSource = Table.ExpandTableColumn(JoinedTables, "news_sources", {"source"}, {"source"}),

    RemovedSourceId = Table.RemoveColumns(ExpandedSource, {"source_id"}),

    ReorderedColumns = Table.SelectColumns(RemovedSourceId, {
        "title", "date", "url", "content", "keyword", "source"
    }),

    // ── FIX: format date as M/d/yyyy agar sama dengan SharePoint ──
    AddBeritaPilihan = Table.AddColumn(ReorderedColumns, "Berita Pilihan",
        each "[" & Date.ToText([date], "M/d/yyyy") & "] " & [title] & " - " & [source]),

    SortedRows = Table.Sort(AddBeritaPilihan, {{"date", Order.Descending}}),

    ChangedType = Table.TransformColumnTypes(SortedRows, {
        {"title", type text},
        {"date", type date},
        {"url", type text},
        {"content", type text},
        {"keyword", type text},
        {"source", type text},
        {"Berita Pilihan", type text}
    })
in
    ChangedType