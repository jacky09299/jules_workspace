import UIKit
import PlaygroundSupport
import UniformTypeIdentifiers

// MARK: – 1. Difficulty 列舉
enum Difficulty: String, CaseIterable, Codable {
    case hard, medium, easy

    var weight: Int {
        switch self {
        case .hard:   return 4
        case .medium: return 2
        case .easy:   return 1
        }
    }

    var title: String {
        switch self {
        case .hard:   return "困難"
        case .medium: return "中等"
        case .easy:   return "簡單"
        }
    }

    init?(title: String) {
        for level in Difficulty.allCases { if level.title == title { self = level; return } }
        return nil
    }
}

// MARK: – 2. Flashcard 結構
struct Flashcard: Identifiable {
    let word: String
    let translation: String
    var difficulty: Difficulty
    var id: String { word }

    var reviewCount: Int = 0
    var lastReviewedDate: Date? = nil
    var consecutiveCorrectStreak: Int = 0
    var timesInLearningQueue: Int = 0
    var consecutiveHardCount: Int = 0 // New property
    var nextReviewDate: Date? = nil   // New property
}

// MARK: – New VocabularySetMetadata Structure
struct VocabularySetMetadata: Codable {
    let id: UUID // Unique ID for this metadata entry
    var bookmarkData: Data? // Security-scoped bookmark for the .txt file
    var lastKnownDisplayName: String
    var lastKnownPath: String // Store the path as a fallback/debug info
    let progressFileUUID: UUID // UUID for the progress data file
}

// MARK: – 3. 字卡內容解析函式
func parseFlashcards(from content: String, filenameForLogging: String) -> [Flashcard] {
    print("📄 開始解析檔案: \(filenameForLogging)")
    return content.split(separator: "\n", omittingEmptySubsequences: true).compactMap { line in
        let parts = line.split(separator: ":", omittingEmptySubsequences: false)
        if parts.count >= 2 {
            let word = String(parts[0].trimmingCharacters(in: .whitespacesAndNewlines))
            let translation = String(parts.last!.trimmingCharacters(in: .whitespacesAndNewlines))
            if !word.isEmpty && !translation.isEmpty {
                return Flashcard(word: word, translation: translation, difficulty: .medium)
            } else {
                print("⚠️ 解析警告 (檔案: \(filenameForLogging)): 詞或翻譯為空 on line '\(line)'")
                return nil
            }
        } else if !line.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            print("⚠️ 解析警告 (檔案: \(filenameForLogging)): 格式不正確 (缺少冒號) on line '\(line)'")
            return nil
        }
        return nil
    }
}

// MARK: – Progress Manager
class ProgressManager {
    static let shared = ProgressManager()
    var vocabularySets: [VocabularySetMetadata] = []
    private let manifestFilename = "vocabulary_sets_manifest.json"

    private init() { // Made private to control initialization
        if isCloudKitEnabled() {
            print("☁️ iCloud is available.")
        } else {
            print("⚠️ iCloud is unavailable or not configured.")
        }
        loadManifest()
    }
    
    func isCloudKitEnabled() -> Bool {
        return FileManager.default.ubiquityIdentityToken != nil
    }
    
    private func getAppDocumentsDirectory() -> URL? {
        do {
            return try FileManager.default.url(for: .documentDirectory,
                                               in: .userDomainMask,
                                               appropriateFor: nil,
                                               create: true)
        } catch {
            print("🚫 無法取得 App 文件目錄: \(error)")
            return nil
        }
    }

    func loadManifest() {
        guard let docDir = getAppDocumentsDirectory() else {
            print("🚫 無法取得文件目錄以載入資訊清單。")
            return
        }
        let manifestURL = docDir.appendingPathComponent(manifestFilename)

        guard FileManager.default.fileExists(atPath: manifestURL.path) else {
            print("ℹ️ 資訊清單檔案不存在於: \(manifestURL.path)。這對於首次執行是正常的。")
            return
        }

        do {
            let data = try Data(contentsOf: manifestURL)
            let decoder = JSONDecoder()
            self.vocabularySets = try decoder.decode([VocabularySetMetadata].self, from: data)
            print("✅ 資訊清單已載入，共 \(vocabularySets.count) 個項目，從: \(manifestURL.path)")
        } catch {
            print("🚫 載入或解碼資訊清單時發生錯誤: \(error) 從路徑: \(manifestURL.path)")
            // Consider deleting the corrupt manifest or attempting a backup restore if errors persist
        }
    }

    func saveManifest() {
        guard let docDir = getAppDocumentsDirectory() else {
            print("🚫 無法取得文件目錄以儲存資訊清單。")
            return
        }
        let manifestURL = docDir.appendingPathComponent(manifestFilename)
        let encoder = JSONEncoder()
        encoder.outputFormatting = .prettyPrinted

        do {
            let data = try encoder.encode(self.vocabularySets)
            try data.write(to: manifestURL, options: [.atomicWrite])
            print("💾 資訊清單已儲存至: \(manifestURL.path)")
        } catch {
            print("🚫 儲存資訊清單時發生錯誤: \(error) 到路徑: \(manifestURL.path)")
        }
    }

    func resolveBookmark(data: Data) -> URL? {
        var isStale = false
        do {
            // Options changed from .withSecurityScope to []
            let url = try URL(resolvingBookmarkData: data,
                              options: [], // <--- MODIFIED HERE
                              relativeTo: nil,
                              bookmarkDataIsStale: &isStale)

            if isStale {
                print("⚠️ 書籤已過期，需要重新建立。 URL: \(String(describing: url))")
                // Attempt to create a new bookmark if possible, or notify user.
                // For now, just returning nil as per original plan for stale.
                // If bookmark is stale, it's possible it can't be resolved without .withSecurityScope,
                // but the primary goal here is to attempt resolution with [], then let the
                // startAccessingSecurityScopedResource() call handle the security scope.
                // If it's stale, it's likely the startAccessing... will fail if the resource moved
                // or permissions changed significantly.
                
                // Re-create the bookmark data. This requires security scope.
                // We need to re-obtain the original URL, which we don't have directly if stale.
                // This part of the logic might need reconsideration if stale bookmarks become problematic.
                // For now, if it's stale, we will return nil as before. The calling code in
                // documentPicker will then attempt to re-establish a bookmark if the user re-picks the file.
                return nil
            }

            // The original logic for starting security scope access remains.
            // FlashcardViewController expects this to be called here.
            if url.startAccessingSecurityScopedResource() {
                // Caller is responsible for calling stopAccessingSecurityScopedResource()
                return url
            } else {
                print("🚫 無法開始安全範圍資源存取。 URL: \(url)")
                return nil
            }
        } catch {
            print("🚫 解析書籤時發生錯誤: \(error)")
            return nil
        }
    }

    func saveProgress(for progressFileUUID: UUID, cards: [Flashcard]) {
        guard let docDir = getAppDocumentsDirectory() else {
            print("🚫 無法取得文件目錄以儲存進度 for \(progressFileUUID)。")
            return
        }
        let progressFileURL = docDir.appendingPathComponent("\(progressFileUUID.uuidString).json")
        
        var progressToSave: [String: [String: Any]] = [:]
        cards.forEach { card in
            var cardData: [String: Any] = [:]
            cardData["difficultyTitle"] = card.difficulty.title
            cardData["consecutiveHardCount"] = card.consecutiveHardCount
            if let nextReviewDate = card.nextReviewDate {
                cardData["nextReviewDateInterval"] = nextReviewDate.timeIntervalSinceReferenceDate
            }
            progressToSave[card.id] = cardData
        }

        let encoder = JSONEncoder()
        encoder.outputFormatting = .prettyPrinted

        do {
            let data = try encoder.encode(progressToSave)
            try data.write(to: progressFileURL, options: [.atomicWrite])
            print("💾 字卡進度 \(progressFileUUID.uuidString) 已儲存至: \(progressFileURL.lastPathComponent)")
        } catch {
            print("🚫 儲存字卡進度時發生錯誤 for \(progressFileUUID): \(error) 至 \(progressFileURL.lastPathComponent)")
        }
    }

    func loadProgress(for progressFileUUID: UUID) -> [String: [String: Any]] {
        guard let docDir = getAppDocumentsDirectory() else {
            print("🚫 無法取得文件目錄以載入進度 for \(progressFileUUID)。")
            return [:]
        }
        let progressFileURL = docDir.appendingPathComponent("\(progressFileUUID.uuidString).json")

        guard FileManager.default.fileExists(atPath: progressFileURL.path) else {
            print("ℹ️ 字卡進度檔案不存在: \(progressFileURL.lastPathComponent) for UUID: \(progressFileUUID.uuidString)")
            return [:]
        }

        do {
            let data = try Data(contentsOf: progressFileURL)
            let decoder = JSONDecoder()
            let progressData = try decoder.decode([String: [String: Any]].self, from: data)
            print("✅ 字卡進度 \(progressFileUUID.uuidString) 已從 \(progressFileURL.lastPathComponent) 載入")
            return progressData
        } catch {
            print("🚫 載入或解碼字卡進度時發生錯誤 for \(progressFileUUID): \(error) 從 \(progressFileURL.lastPathComponent)")
            return [:]
        }
    }
}

// MARK: – 5. Review Analysis ViewController
class ReviewAnalysisViewController: UIViewController, UITableViewDataSource, UITableViewDelegate {
    var cards: [Flashcard] = []

    private let tableView: UITableView = {
        let tv = UITableView(frame: .zero, style: .insetGrouped)
        tv.translatesAutoresizingMaskIntoConstraints = false
        tv.register(UITableViewCell.self, forCellReuseIdentifier: "AnalysisCell")
        return tv
    }()

    private var statsSectionData: [(title: String, value: String)] = []
    private var hardCardsData: [Flashcard] = []
    private var mediumCardsData: [Flashcard] = []
    private var easyCardsData: [Flashcard] = []

    enum SectionType: Int, CaseIterable {
        case statistics, hard, medium, easy
        var title: String {
            switch self {
            case .statistics: return "整體統計"
            case .hard: return "困難字卡"
            case .medium: return "中等字卡"
            case .easy: return "簡單字卡"
            }
        }
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        title = "複習狀況分析"
        if #available(iOS 13.0, *) {
            view.backgroundColor = .systemGroupedBackground
            navigationItem.rightBarButtonItem = UIBarButtonItem(barButtonSystemItem: .done, target: self, action: #selector(doneButtonTapped))
        } else {
            view.backgroundColor = .groupTableViewBackground
            navigationItem.rightBarButtonItem = UIBarButtonItem(title: "完成", style: .done, target: self, action: #selector(doneButtonTapped))
        }
        prepareDataForDisplay()
        tableView.dataSource = self
        tableView.delegate = self
        view.addSubview(tableView)
        NSLayoutConstraint.activate([
            tableView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            tableView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            tableView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            tableView.bottomAnchor.constraint(equalTo: view.bottomAnchor)
        ])
    }

    @objc private func doneButtonTapped() {
        dismiss(animated: true, completion: nil)
    }

    private func prepareDataForDisplay() {
        statsSectionData.removeAll(); hardCardsData.removeAll(); mediumCardsData.removeAll(); easyCardsData.removeAll()
        let total = cards.count
        guard total > 0 else { // This guard has a return
            statsSectionData.append(("總字卡數", "0"))
            statsSectionData.append(("提示", "請先載入並複習字卡"))
            return
        }
        hardCardsData = cards.filter{$0.difficulty == .hard}.sorted{$0.word.localizedCompare($1.word) == .orderedAscending}
        mediumCardsData = cards.filter{$0.difficulty == .medium}.sorted{$0.word.localizedCompare($1.word) == .orderedAscending}
        easyCardsData = cards.filter{$0.difficulty == .easy}.sorted{$0.word.localizedCompare($1.word) == .orderedAscending}
        statsSectionData.append(("總字卡數", "\(total)"))
        func statItem(for diff: Difficulty, count: Int) -> (String, String) {
            (diff.title, "\(count) (\(String(format: "%.1f%%", total > 0 ? Double(count)*100.0/Double(total) : 0.0)))")
        }
        statsSectionData.append(statItem(for: .hard, count: hardCardsData.count))
        statsSectionData.append(statItem(for: .medium, count: mediumCardsData.count))
        statsSectionData.append(statItem(for: .easy, count: easyCardsData.count))
    }

    func numberOfSections(in tableView: UITableView) -> Int { SectionType.allCases.count }

    func tableView(_ tableView: UITableView, titleForHeaderInSection section: Int) -> String? {
        guard let type = SectionType(rawValue: section) else { return nil }
        func countForType() -> Int {
            switch type { case .hard: return hardCardsData.count; case .medium: return mediumCardsData.count; case .easy: return easyCardsData.count; default: return 0 }
        }
        let count = countForType()
        if type == .statistics || count > 0 { return "\(type.title)\(type != .statistics ? " (\(count))" : "")" }
        return nil
    }

    func tableView(_ tableView: UITableView, heightForHeaderInSection section: Int) -> CGFloat {
        guard let type = SectionType(rawValue: section) else { return UITableView.automaticDimension }
        func isEmpty() -> Bool {
            switch type { case .hard: return hardCardsData.isEmpty; case .medium: return mediumCardsData.isEmpty; case .easy: return easyCardsData.isEmpty; default: return false }
        }
        if type != .statistics && isEmpty() { return 0.1 }
        return UITableView.automaticDimension
    }

    func tableView(_ tableView: UITableView, heightForFooterInSection section: Int) -> CGFloat { return 0.1 }

    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        guard let type = SectionType(rawValue: section) else { return 0 }
        switch type {
        case .statistics: return statsSectionData.count
        case .hard: return hardCardsData.count
        case .medium: return mediumCardsData.count
        case .easy: return easyCardsData.count
        }
    }

    func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: "AnalysisCell", for: indexPath)
        // Initialize config here to ensure it's always set before guard
        var config: UIListContentConfiguration? = nil // Optional for iOS 14+
        if #available(iOS 14.0, *) {
            config = UIListContentConfiguration.valueCell() // Default for stats
        }

        guard let type = SectionType(rawValue: indexPath.section) else {
            if #available(iOS 14.0, *) {
                var errorConfig = UIListContentConfiguration.cell()
                errorConfig.text = "錯誤: 無效區塊"
                cell.contentConfiguration = errorConfig
            } else { cell.textLabel?.text = "錯誤: 無效區塊"; cell.detailTextLabel?.text = "" }
            return cell // GUARD EXIT
        }

        if #available(iOS 14.0, *) {
            // Re-assign config based on type for iOS 14+
            switch type {
            case .statistics: config = UIListContentConfiguration.valueCell()
            case .hard, .medium, .easy: config = UIListContentConfiguration.subtitleCell()
            }
            
            // Now populate the config
            switch type {
            case .statistics:
                let stat = statsSectionData[indexPath.row]
                config?.text = stat.title; config?.secondaryText = stat.value
            case .hard, .medium, .easy:
                let card: Flashcard
                if type == .hard { card = hardCardsData[indexPath.row] }
                else if type == .medium { card = mediumCardsData[indexPath.row] }
                else { card = easyCardsData[indexPath.row] }
                config?.text = card.word; config?.secondaryText = card.translation
            }
            cell.contentConfiguration = config
        } else {
            // Fallback for iOS < 14
            cell.textLabel?.text = "" // Clear previous
            cell.detailTextLabel?.text = "" // Clear previous
            switch type {
            case .statistics:
                let stat = statsSectionData[indexPath.row]
                cell.textLabel?.text = stat.title; cell.detailTextLabel?.text = stat.value
                cell.detailTextLabel?.textColor = .gray
            case .hard, .medium, .easy:
                let card: Flashcard
                if type == .hard { card = hardCardsData[indexPath.row] }
                else if type == .medium { card = mediumCardsData[indexPath.row] }
                else { card = easyCardsData[indexPath.row] }
                cell.textLabel?.text = card.word; cell.detailTextLabel?.text = card.translation
                cell.detailTextLabel?.textColor = .gray
            }
        }
        
        cell.selectionStyle = .none
        return cell
    }
}

// MARK: – 4. Flashcard ViewController
class FlashcardViewController: UIViewController, UIDocumentPickerDelegate {

    private var currentVocabularySet: VocabularySetMetadata?
    private var currentFileDisplayName: String? { // This property might become redundant if currentVocabularySet is always the source of truth
        didSet { title = currentVocabularySet != nil ? "字卡: \(currentVocabularySet!.lastKnownDisplayName)" : "字卡複習" }
    }
    private var allCards: [Flashcard] = []
    // private var learningQueue: [Flashcard] = [] // Removed
    private var reviewPool: [Flashcard] = []
    private var currentCard: Flashcard?
    private var isShowingAnswer: Bool = false

    private let cardView: UIView = {
        let view = UIView()
        view.layer.cornerRadius = 12
        view.layer.shadowColor = UIColor.black.cgColor
        view.layer.shadowOpacity = 0.15; view.layer.shadowOffset = CGSize(width: 0, height: 1); view.layer.shadowRadius = 3
        view.translatesAutoresizingMaskIntoConstraints = false
        return view
    }()

    private let cardLabel: UILabel = {
        let lbl = UILabel()
        lbl.font = .systemFont(ofSize: 48, weight: .bold)
        lbl.textAlignment = .center
        lbl.numberOfLines = 1
        lbl.adjustsFontSizeToFitWidth = true
        lbl.minimumScaleFactor = 0.3
        lbl.translatesAutoresizingMaskIntoConstraints = false
        return lbl
    }()
    
    private let translationLabel: UILabel = {
        let lbl = UILabel()
        lbl.font = .systemFont(ofSize: 32, weight: .bold)
        lbl.textAlignment = .center
        lbl.numberOfLines = 0
        lbl.translatesAutoresizingMaskIntoConstraints = false
        lbl.isHidden = true
        return lbl
    }()

    private let cardCountLabel: UILabel = {
        let lbl = UILabel()
        lbl.font = .systemFont(ofSize: 14, weight: .regular)
        lbl.textAlignment = .center
        lbl.translatesAutoresizingMaskIntoConstraints = false
        return lbl
    }()

    private lazy var flipButton: UIButton = {
        let btn = UIButton(type: .system)
        btn.setTitle("顯示答案", for: .normal)
        btn.titleLabel?.font = .systemFont(ofSize: 18, weight: .semibold)
        btn.layer.cornerRadius = 8
        btn.translatesAutoresizingMaskIntoConstraints = false
        btn.addTarget(self, action: #selector(flipCardAction), for: .touchUpInside)
        return btn
    }()

    private let difficultyStack: UIStackView = {
        let sv = UIStackView()
        sv.axis = .horizontal
        sv.distribution = .fillEqually
        sv.spacing = 10
        sv.translatesAutoresizingMaskIntoConstraints = false
        return sv
    }()
    
    private lazy var loadFileButton: UIButton = {
        let btn = UIButton(type: .system)
        btn.setTitle(" 載入字卡檔 (.txt)", for: .normal)
        btn.titleLabel?.font = .systemFont(ofSize: 18, weight: .semibold)
        btn.layer.cornerRadius = 8
        btn.contentEdgeInsets = UIEdgeInsets(top: 0, left: 10, bottom: 0, right: 10)
        btn.translatesAutoresizingMaskIntoConstraints = false
        btn.addTarget(self, action: #selector(loadFileButtonTapped), for: .touchUpInside)
        return btn
    }()
    
    private let reviewPoolTargetSize = 25
    private let learningRepetitions = 2
    private let graduatedThreshold = 3

    override func viewDidLoad() {
        super.viewDidLoad()
        applyDynamicStyling()
        setupUI()
        updateUIForNoFileLoaded()
        var analysisBarButton: UIBarButtonItem
        if #available(iOS 13.0, *) {
            analysisBarButton = UIBarButtonItem(title: "分析", image: UIImage(systemName: "chart.pie"), target: self, action: #selector(showAnalysisTapped))
        } else {
            analysisBarButton = UIBarButtonItem(title: "分析", style: .plain, target: self, action: #selector(showAnalysisTapped))
        }
        navigationItem.rightBarButtonItem = analysisBarButton
        navigationItem.rightBarButtonItem?.isEnabled = false
    }

    private func applyDynamicStyling() {
        if #available(iOS 13.0, *) {
            view.backgroundColor = .systemGray6
            cardView.backgroundColor = .secondarySystemGroupedBackground
            cardLabel.textColor = .label
            translationLabel.textColor = .label
            cardCountLabel.textColor = .secondaryLabel
            flipButton.backgroundColor = .systemBlue; flipButton.setTitleColor(.white, for: .normal)
            loadFileButton.setImage(UIImage(systemName: "doc.text.fill"), for: .normal)
            loadFileButton.tintColor = .white; loadFileButton.backgroundColor = .systemGreen; loadFileButton.setTitleColor(.white, for: .normal)
        } else {
            view.backgroundColor = UIColor(red: 0.95, green: 0.95, blue: 0.97, alpha: 1.0)
            cardView.backgroundColor = .white
            cardLabel.textColor = .black; translationLabel.textColor = .black
            cardCountLabel.textColor = .gray
            flipButton.backgroundColor = .blue; flipButton.setTitleColor(.white, for: .normal)
            loadFileButton.backgroundColor = .green; loadFileButton.setTitleColor(.white, for: .normal)
        }
    }

    private func setupUI() {
        cardView.addSubview(cardLabel); cardView.addSubview(translationLabel)
        view.addSubview(loadFileButton); view.addSubview(cardView); view.addSubview(cardCountLabel)
        view.addSubview(flipButton); view.addSubview(difficultyStack)
        Difficulty.allCases.forEach { diff in
            let btn = UIButton(type: .system)
            btn.setTitle(diff.title, for: .normal); btn.titleLabel?.font = .systemFont(ofSize: 16, weight: .medium)
            btn.tag = diff.weight; btn.addTarget(self, action: #selector(difficultyTapped(_:)), for: .touchUpInside)
            btn.isHidden = true; btn.layer.cornerRadius = 8; btn.layer.borderWidth = 1
            if #available(iOS 13.0, *) { btn.layer.borderColor = UIColor.systemBlue.cgColor; btn.setTitleColor(.systemBlue, for: .normal) }
            else { btn.layer.borderColor = UIColor.blue.cgColor; btn.setTitleColor(.blue, for: .normal) }
            difficultyStack.addArrangedSubview(btn)
        }
        NSLayoutConstraint.activate([
            loadFileButton.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 15),
            loadFileButton.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            loadFileButton.leadingAnchor.constraint(greaterThanOrEqualTo: view.leadingAnchor, constant: 20),
            loadFileButton.trailingAnchor.constraint(lessThanOrEqualTo: view.trailingAnchor, constant: -20),
            loadFileButton.heightAnchor.constraint(equalToConstant: 44),
            cardView.topAnchor.constraint(equalTo: loadFileButton.bottomAnchor, constant: 20),
            cardView.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            cardView.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20),
            cardView.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20),
            cardView.heightAnchor.constraint(equalTo: cardView.widthAnchor, multiplier: 0.6),
            cardLabel.centerXAnchor.constraint(equalTo: cardView.centerXAnchor),
            cardLabel.centerYAnchor.constraint(equalTo: cardView.centerYAnchor),
            cardLabel.leadingAnchor.constraint(equalTo: cardView.leadingAnchor, constant: 10),
            cardLabel.trailingAnchor.constraint(equalTo: cardView.trailingAnchor, constant: -10),
            translationLabel.centerXAnchor.constraint(equalTo: cardView.centerXAnchor),
            translationLabel.centerYAnchor.constraint(equalTo: cardView.centerYAnchor),
            translationLabel.leadingAnchor.constraint(equalTo: cardView.leadingAnchor, constant: 10),
            translationLabel.trailingAnchor.constraint(equalTo: cardView.trailingAnchor, constant: -10),
            cardCountLabel.topAnchor.constraint(equalTo: cardView.bottomAnchor, constant: 10),
            cardCountLabel.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            flipButton.topAnchor.constraint(equalTo: cardCountLabel.bottomAnchor, constant: 20),
            flipButton.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            flipButton.widthAnchor.constraint(equalToConstant: 150),
            flipButton.heightAnchor.constraint(equalToConstant: 44),
            difficultyStack.topAnchor.constraint(equalTo: flipButton.bottomAnchor, constant: 25),
            difficultyStack.leadingAnchor.constraint(equalTo: view.layoutMarginsGuide.leadingAnchor, constant: 20),
            difficultyStack.trailingAnchor.constraint(equalTo: view.layoutMarginsGuide.trailingAnchor, constant: -20),
            difficultyStack.heightAnchor.constraint(equalToConstant: 40),
        ])
        cardView.addGestureRecognizer(UITapGestureRecognizer(target: self, action: #selector(flipCardAction)))
    }
    
    private func updateUIForNoFileLoaded() {
        cardLabel.text = "請點擊上方按鈕載入字卡檔 (.txt)"; cardLabel.font = .systemFont(ofSize: 18)
        translationLabel.isHidden = true; flipButton.isHidden = true
        difficultyStack.arrangedSubviews.forEach { $0.isHidden = true }
        cardCountLabel.text = "未載入檔案"
        allCards.removeAll(); reviewPool.removeAll(); currentCard = nil
        currentVocabularySet = nil // Ensure currentVocabularySet is reset
        currentFileDisplayName = nil // Also reset display name
        navigationItem.rightBarButtonItem?.isEnabled = false
    }

    @objc private func loadFileButtonTapped() {
        let picker: UIDocumentPickerViewController
        if #available(iOS 14.0, *) { picker = UIDocumentPickerViewController(forOpeningContentTypes: [UTType.text], asCopy: true) }
        else { picker = UIDocumentPickerViewController(documentTypes: ["public.plain-text"], in: .import) }
        picker.delegate = self; present(picker, animated: true)
    }

    func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
        guard let url = urls.first else { return }
        let access = url.startAccessingSecurityScopedResource(); defer { if access { url.stopAccessingSecurityScopedResource() } }

        do {
            // Save progress for the previous file if one was loaded
            if let previousSet = currentVocabularySet, !allCards.isEmpty {
                ProgressManager.shared.saveProgress(for: previousSet.progressFileUUID, cards: allCards)
                print("💾 先前字卡集 \(previousSet.lastKnownDisplayName) 的進度已儲存。")
            }

            let filename = url.lastPathComponent
            let displayName = url.deletingPathExtension().lastPathComponent
            var VSM_for_picked_file: VocabularySetMetadata? = nil

            // Find existing VocabularySetMetadata by resolving bookmarks
            for i in 0..<ProgressManager.shared.vocabularySets.count { // Use index for potential modification
                var set = ProgressManager.shared.vocabularySets[i]
                if let bookmarkData = set.bookmarkData {
                    if let resolvedURL = ProgressManager.shared.resolveBookmark(data: bookmarkData) {
                        // Important: stopAccessingSecurityScopedResource for the resolvedURL from bookmark
                        // This is crucial because resolveBookmark starts access.
                        defer { resolvedURL.stopAccessingSecurityScopedResource() }
                        
                        if resolvedURL == url {
                            VSM_for_picked_file = set
                            print("ℹ️ 透過書籤找到現有字卡集: \(set.lastKnownDisplayName)")
                            // Check if path or display name needs update (e.g., file moved)
                            var manifestNeedsSave = false
                            if set.lastKnownPath != url.path {
                                print("⚠️ 路徑已變更: \(set.lastKnownPath) -> \(url.path)")
                                set.lastKnownPath = url.path
                                manifestNeedsSave = true
                            }
                            if set.lastKnownDisplayName != displayName {
                                print("⚠️ 顯示名稱已變更: \(set.lastKnownDisplayName) -> \(displayName)")
                                set.lastKnownDisplayName = displayName
                                manifestNeedsSave = true
                            }
                            // Re-create bookmark data as it might have changed or the old one was stale
                            do {
                                let newBookmarkData = try url.bookmarkData(options: .minimalBookmark, includingResourceValuesForKeys: nil, relativeTo: nil)
                                if set.bookmarkData != newBookmarkData { // Avoid unnecessary saves if data is identical
                                    print("🔄 更新書籤資料 for \(displayName)")
                                    set.bookmarkData = newBookmarkData
                                    manifestNeedsSave = true
                                }
                            } catch {
                                print("🚫 無法為 \(displayName) 建立新書籤: \(error)")
                                // Potentially mark this set as needing attention or remove bookmark
                            }

                            if manifestNeedsSave {
                                ProgressManager.shared.vocabularySets[i] = set // Update in array
                                ProgressManager.shared.saveManifest()
                            }
                            break
                        }
                    } else {
                        print("⚠️ 無法解析 \(set.lastKnownDisplayName) 的書籤。可能需要重新選擇檔案。")
                        // Optionally, remove the stale bookmarkData here or mark the set
                        // For now, we'll let it be, user might re-pick and update it.
                    }
                }
            }

            if VSM_for_picked_file == nil {
                print("ℹ️ 未找到現有字卡集，將為 \(displayName) 建立新項目。")
                var newBookmarkData: Data? = nil
                do {
                    newBookmarkData = try url.bookmarkData(options: .minimalBookmark, includingResourceValuesForKeys: nil, relativeTo: nil)
                } catch {
                    print("🚫 為 \(displayName) 建立書籤時發生錯誤: \(error)")
                    // Proceed without bookmark, or show an error to the user
                }
                let newSet = VocabularySetMetadata(id: UUID(),
                                                   bookmarkData: newBookmarkData,
                                                   lastKnownDisplayName: displayName,
                                                   lastKnownPath: url.path,
                                                   progressFileUUID: UUID())
                ProgressManager.shared.vocabularySets.append(newSet)
                ProgressManager.shared.saveManifest()
                VSM_for_picked_file = newSet
            }

            self.currentVocabularySet = VSM_for_picked_file
            self.currentFileDisplayName = self.currentVocabularySet?.lastKnownDisplayName // Update display name

            // Parse Flashcards
            let content = try String(contentsOf: url, encoding: .utf8)
            cardLabel.text = ""; cardLabel.font = .systemFont(ofSize: 48, weight: .bold); translationLabel.isHidden = true
            let parsedCards = parseFlashcards(from: content, filenameForLogging: filename)

            if parsedCards.isEmpty {
                updateUIForNoFileLoaded() // This will set currentVocabularySet to nil
                // Explicitly set currentVocabularySet for this empty file for clarity, though updateUIForNoFileLoaded handles it.
                // self.currentVocabularySet = VSM_for_picked_file
                // self.currentFileDisplayName = self.currentVocabularySet?.lastKnownDisplayName
                cardLabel.text = "檔案 \(filename)\n是空的或格式不正確。"; cardLabel.font = .systemFont(ofSize: 18); return
            }
            
            var loadedProgressToApply: [String: [String: Any]] = [:]
            let oldUserDefaultsKey = url.lastPathComponent + "flashcardFileProgress_ipad_v4_"

            if let legacyData = UserDefaults.standard.dictionary(forKey: oldUserDefaultsKey) as? [String: [String: Any]], !legacyData.isEmpty {
                print("⏳ 進行舊進度移轉 for \(filename)...")
                loadedProgressToApply = legacyData
                
                // Temporarily map legacy data to allCards structure for saving
                let tempCardsForSavingMigration = parsedCards.map { pCard -> Flashcard in
                    var card = pCard
                    if let progressData = legacyData[card.id] {
                        if let difficultyTitle = progressData["difficultyTitle"] as? String, let diff = Difficulty(title: difficultyTitle) { card.difficulty = diff }
                        if let hardCount = progressData["consecutiveHardCount"] as? Int { card.consecutiveHardCount = hardCount }
                        if let reviewInterval = progressData["nextReviewDateInterval"] as? Double { card.nextReviewDate = Date(timeIntervalSinceReferenceDate: reviewInterval) }
                    }
                    return card
                }
                ProgressManager.shared.saveProgress(for: self.currentVocabularySet!.progressFileUUID, cards: tempCardsForSavingMigration)
                UserDefaults.standard.removeObject(forKey: oldUserDefaultsKey)
                print("✅ 舊進度已移轉並從 UserDefaults 中移除。")
            } else {
                loadedProgressToApply = ProgressManager.shared.loadProgress(for: self.currentVocabularySet!.progressFileUUID)
            }

            allCards = parsedCards.map { pCard in
                var card = pCard
                if let progressData = loadedProgressToApply[card.id] {
                    if let difficultyTitle = progressData["difficultyTitle"] as? String, let diff = Difficulty(title: difficultyTitle) { card.difficulty = diff }
                    if let hardCount = progressData["consecutiveHardCount"] as? Int { card.consecutiveHardCount = hardCount }
                    if let reviewInterval = progressData["nextReviewDateInterval"] as? Double { card.nextReviewDate = Date(timeIntervalSinceReferenceDate: reviewInterval) }
                    else { card.nextReviewDate = nil }
                }
                return card
            }

            print("✅ 載入 \(filename) (來自 \(self.currentVocabularySet?.lastKnownPath ?? "未知路徑")), 共 \(allCards.count) 張。運行時複習狀態已重置。")
            reviewPool.removeAll(); fillReviewPool()
            navigationItem.rightBarButtonItem?.isEnabled = !allCards.isEmpty; loadNextCard()

        } catch {
            print("🚫 讀取檔案或處理字卡集時發生錯誤: \(error)")
            updateUIForNoFileLoaded()
        }
    }
    func documentPickerWasCancelled(_ controller: UIDocumentPickerViewController) { print("ℹ️ 取消選擇") }

    private func fillReviewPool() {
        let currentSize = reviewPool.count // learningQueue.count removed
        if currentSize >= reviewPoolTargetSize && !reviewPool.isEmpty { return }
        let needed = reviewPoolTargetSize - currentSize; if needed <= 0 && !reviewPool.isEmpty { return }
        print("ℹ️ 填充複習池，需 \(max(0, needed))。 RP:\(reviewPool.count)") // LQ print removed
        let existingIDs = Set(reviewPool.map{$0.id}) // learningQueue.map removed
        let now = Date() // Get current date once for consistent comparison

        let candidates = allCards.filter { card in
            !existingIDs.contains(card.id) &&
            (card.nextReviewDate == nil || card.nextReviewDate! <= now)
        }.sorted { c1, c2 in
            // 1. Sort by difficulty (harder first)
            if c1.difficulty.weight != c2.difficulty.weight { return c1.difficulty.weight > c2.difficulty.weight }
            
            // 2. Avoid graduated easy cards (unless all/most are graduated)
            let c1Grad = (c1.difficulty == .easy && c1.consecutiveCorrectStreak >= graduatedThreshold)
            let c2Grad = (c2.difficulty == .easy && c2.consecutiveCorrectStreak >= graduatedThreshold)
            // If one is graduated and the other not, prioritize non-graduated.
            // If both are same graduation status, this doesn't apply, move to next criteria.
            if c1Grad != c2Grad { return !c1Grad } 
            
            // 3. Then by review count (less reviewed first)
            if c1.reviewCount != c2.reviewCount { return c1.reviewCount < c2.reviewCount }
            
            // 4. Then by last reviewed date (older first, or never reviewed first)
            // This implicitly handles cards whose nextReviewDate might have been set long ago
            // and are now due alongside cards that were never spaced.
            if let d1 = c1.lastReviewedDate, let d2 = c2.lastReviewedDate {
                if d1 != d2 { return d1 < d2 } // Sort by actual review date if different
            } else if c1.lastReviewedDate == nil && c2.lastReviewedDate != nil {
                return true // c1 (never reviewed) comes before c2 (reviewed)
            } else if c1.lastReviewedDate != nil && c2.lastReviewedDate == nil {
                return false // c1 (reviewed) comes after c2 (never reviewed)
            }
            // If lastReviewedDates are same (or both nil), could add further tie-breakers if needed,
            // but current structure should be fine. For example, word order for stability.
            return c1.word.localizedCompare(c2.word) == .orderedAscending
        }
        reviewPool.append(contentsOf: candidates.prefix(max(0,needed))); reviewPool.shuffle()
        print("ℹ️ 填充後 RP: \(reviewPool.count)")
    }

    private func pickNextCard() -> Flashcard? {
        // if !learningQueue.isEmpty { print("🎓 從 Learning Queue 取卡"); return learningQueue.removeFirst() } // Removed
        if reviewPool.isEmpty { fillReviewPool() }
        guard !reviewPool.isEmpty else {
            var didReset = false; print("ℹ️ Review Pool 為空，嘗試重置已畢業卡片...")
            for i in 0..<allCards.count {
                if allCards[i].difficulty == .easy && allCards[i].consecutiveCorrectStreak >= graduatedThreshold {
                    allCards[i].consecutiveCorrectStreak = 0
                    allCards[i].lastReviewedDate = nil
                    allCards[i].nextReviewDate = nil   // Added
                    allCards[i].consecutiveHardCount = 0 // Added
                    didReset = true
                    print("🔄 重置卡片 (fully): \(allCards[i].word)")
                }
            }
            if didReset {
                fillReviewPool()
                if reviewPool.isEmpty {
                    print("ℹ️ 重置後 Review Pool 仍為空")
                    return nil
                } else {
                    // reviewPool is now populated. However, to prevent the guard from falling through,
                    // this path must also exit the scope.
                    print("ℹ️ Review Pool was refilled. Exiting guard scope as required for Swift 'guard' semantics. Card will be picked on a subsequent call.")
                    return nil
                }
            } else {
                print("ℹ️ Review Pool 為空且無卡片可重置")
                return nil // Ensure this path also returns
            }
        }
        let card = reviewPool.remove(at: Int.random(in: 0..<reviewPool.count))
        print("📚 從 Review Pool 取卡: \(card.word)")
        return card
    }

    private func loadNextCard() {
        guard !allCards.isEmpty else { updateUIForNoFileLoaded(); return }
        navigationItem.rightBarButtonItem?.isEnabled = true
        if reviewPool.count < reviewPoolTargetSize / 2 { fillReviewPool() }
        if let next = pickNextCard() {
            currentCard = next; isShowingAnswer = false
            cardLabel.isHidden = false; translationLabel.isHidden = true
            cardLabel.text = next.word; translationLabel.text = next.translation
            flipButton.setTitle("顯示答案", for: .normal); flipButton.isHidden = false
            difficultyStack.arrangedSubviews.forEach { $0.isHidden = true }
            let graduatedCount = allCards.filter{ $0.difficulty == .easy && $0.consecutiveCorrectStreak >= graduatedThreshold }.count
            cardCountLabel.text = "待複習:\(reviewPool.count) | 已掌握:\(graduatedCount)" // learningQueue.count removed
        } else {
            cardLabel.text = "🎉 恭喜！\n所有卡片已達學習目標。"; cardLabel.font = .systemFont(ofSize: 18)
            translationLabel.isHidden = true; flipButton.isHidden = true
            difficultyStack.arrangedSubviews.forEach { $0.isHidden = true }
            cardCountLabel.text = "已完成！"; currentCard = nil
        }
    }

    @objc private func flipCardAction() {
        guard currentCard != nil else { return }
        isShowingAnswer.toggle()
        let showWord = !isShowingAnswer
        UIView.transition(with: cardView, duration: 0.5, options: showWord ? .transitionFlipFromLeft : .transitionFlipFromRight, animations: {
            self.cardLabel.isHidden = !showWord
            self.translationLabel.isHidden = showWord
        }) { _ in
            self.flipButton.setTitle(self.isShowingAnswer ? "返回題目" : "顯示答案", for: .normal)
            self.difficultyStack.arrangedSubviews.forEach { $0.isHidden = !self.isShowingAnswer }
        }
    }

    @objc private func difficultyTapped(_ sender: UIButton) {
        guard let cardId = currentCard?.id, let cardIdx = allCards.firstIndex(where: {$0.id == cardId}),
              let vocSet = currentVocabularySet, // Use currentVocabularySet
              let newDiff = Difficulty.allCases.first(where: {$0.weight == sender.tag}) else { return }
        var card = allCards[cardIdx]; let oldDiff = card.difficulty
        card.difficulty = newDiff; card.reviewCount += 1; card.lastReviewedDate = Date()
        // let originalLQCount = learningQueue.count // Removed
        // learningQueue.removeAll(where: {$0.id == card.id}) // Removed
        // if originalLQCount > learningQueue.count { print("ℹ️ \(card.word) 從 LQ 移除，因手動評分。") } // Removed
        // card.timesInLearningQueue = 0 // Removed as its utility diminishes

        switch newDiff {
        case .hard:
            card.consecutiveCorrectStreak = 0
            card.consecutiveHardCount += 1
            let intervalInDays = pow(2.0, Double(card.consecutiveHardCount)) // First interval: 2.0^1 = 2 days
            card.nextReviewDate = Calendar.current.date(byAdding: .day, value: Int(intervalInDays), to: Date())
            print("🔴 \(card.word) 標為困難. Consecutive hard: \(card.consecutiveHardCount). Next review in approx. \(Int(intervalInDays)) days.")
        case .medium:
            card.consecutiveHardCount = 0
            card.nextReviewDate = nil
            card.consecutiveCorrectStreak = (oldDiff == .easy || (oldDiff == .medium && newDiff == .medium)) ? card.consecutiveCorrectStreak + 1 : 1
            print("🟡 \(card.word) 標為中等，Streak:\(card.consecutiveCorrectStreak)")
        case .easy:
            card.consecutiveHardCount = 0
            card.nextReviewDate = nil
            card.consecutiveCorrectStreak += 1
            print("🟢 \(card.word) 標為簡單，Streak:\(card.consecutiveCorrectStreak)")
            if card.consecutiveCorrectStreak >= graduatedThreshold {
                print("🎉 \(card.word) 達到簡單畢業標準!")
                // Optionally set a very distant nextReviewDate for graduated cards, e.g.:
                // card.nextReviewDate = Calendar.current.date(byAdding: .year, value: 100, to: Date())
            }
        }
        allCards[cardIdx] = card
        ProgressManager.shared.saveProgress(for: vocSet.progressFileUUID, cards: allCards) // Use vocSet.progressFileUUID
        UIView.animate(withDuration:0.1, animations:{sender.transform=CGAffineTransform(scaleX:1.1,y:1.1);sender.alpha=0.7})
        { _ in UIView.animate(withDuration:0.2){sender.transform = .identity; sender.alpha=1.0}}
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) { self.loadNextCard() }
    }

    @objc private func showAnalysisTapped() {
        guard !allCards.isEmpty else {
            let alert = UIAlertController(title:"無資料", message:"請先載入字卡", preferredStyle:.alert)
            alert.addAction(UIAlertAction(title:"好", style:.default)); present(alert, animated:true); return
        }
        let vc = ReviewAnalysisViewController(); vc.cards = allCards
        present(UINavigationController(rootViewController: vc), animated: true)
    }
}

// 啟動 Live View
let vc = FlashcardViewController()
let navVC = UINavigationController(rootViewController: vc)
PlaygroundPage.current.liveView = navVC

// --- 如何使用 (與之前相同) ---
// 1. 準備字卡檔案 (.txt) ...
// 2. 執行 Playground ...
// 3. 載入檔案 ...
// 4. 開始複習 ...
// 5. 點擊導覽列右上角的「分析」按鈕查看複習狀況。
// ...
