// (Data)CPO — Azure SQL version
// Fix: tambah kolom DataBiodiesel dengan join ke data_biodiesel_hip on YearMonth
let
    Source = Sql.Database("pei-dashboard.database.windows.net", "pei-dashboard", [HierarchicalNavigation=true, MultiSubnetFailover=true]),
    dbo = Source{[Schema="dbo"]}[Data],
    data_cpo_prices1 = dbo{[Name="data_cpo_prices"]}[Data],
    data_biodiesel_hip1 = dbo{[Name="data_biodiesel_hip"]}[Data],

    // ── Prepare CPO ──
    FilteredRows = Table.SelectRows(data_cpo_prices1, each [px_last] <> null),

    RenamedColumns = Table.RenameColumns(FilteredRows, {
        {"upload_date", "Upload_Dates"},
        {"price_date", "Dates"}
    }),

    AddYearMonthFormat = Table.AddColumn(RenamedColumns, "YearMonth_CPO",
        each Text.From(Date.Year([Dates])) & Text.PadStart(Text.From(Date.Month([Dates])), 2, "0"),
        type text),

    SelectedColumns = Table.SelectColumns(AddYearMonthFormat, {
        "Upload_Dates", "Dates", "px_last", "YearMonth_CPO"
    }),

    RenamePrice = Table.RenameColumns(SelectedColumns, {
        {"px_last", "PX_LAST"}
    }),

    // ── Prepare Biodiesel HIP: convert "Januari 2026" → "202601" ──
    MonthMap = [
        Januari="01", Februari="02", Maret="03", April="04",
        Mei="05", Juni="06", Juli="07", Agustus="08",
        September="09", Oktober="10", November="11", Desember="12"
    ],

    AddBiodieselYM = Table.AddColumn(data_biodiesel_hip1, "YM_Biodiesel",
        each
            let
                parts     = Text.Split([hip_month], " "),
                monthName = parts{0},
                year      = parts{1},
                monthNum  = Record.Field(MonthMap, monthName)
            in
                year & monthNum,
        type text),

    BiodieselSelected = Table.SelectColumns(AddBiodieselYM, {"YM_Biodiesel", "price_idr_liter"}),

    // ── Join CPO ← Biodiesel on YearMonth (LeftOuter) ──
    JoinedTable = Table.NestedJoin(RenamePrice, {"YearMonth_CPO"}, BiodieselSelected, {"YM_Biodiesel"}, "Biodiesel", JoinKind.LeftOuter),

    ExpandedBiodiesel = Table.ExpandTableColumn(JoinedTable, "Biodiesel", {"price_idr_liter"}, {"DataBiodiesel"}),

    SortedRows = Table.Sort(ExpandedBiodiesel, {{"Dates", Order.Ascending}}),

    ChangedType = Table.TransformColumnTypes(SortedRows, {
        {"Upload_Dates", type date},
        {"Dates", type date},
        {"PX_LAST", type number},
        {"YearMonth_CPO", type text},
        {"DataBiodiesel", type number}
    }),

    #"Filtered Rows" = Table.SelectRows(ChangedType, each true)
in
    #"Filtered Rows"
