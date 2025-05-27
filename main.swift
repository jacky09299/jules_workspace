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
    private let userDefaults = UserDefaults.standard
    private let progressPrefix = "flashcardFileProgress_ipad_v4_"

    private func progressKey(for filename: String) -> String {
        return URL(fileURLWithPath: filename).lastPathComponent + progressPrefix
    }

    func saveProgress(for filename: String, cards: [Flashcard]) {
        var progressToSave: [String: String] = [:]
        cards.forEach { progressToSave[$0.id] = $0.difficulty.title }
        userDefaults.set(progressToSave, forKey: progressKey(for: filename))
        print("💾 進度 (Difficulty) 已儲存: \(URL(fileURLWithPath: filename).lastPathComponent)")
    }

    func loadProgress(for filename: String) -> [String: Difficulty] {
        let key = progressKey(for: filename)
        guard let saved = userDefaults.dictionary(forKey: key) as? [String: String] else {
            print("ℹ️ 找不到 \(URL(fileURLWithPath: filename).lastPathComponent) 的 Difficulty 進度 (Key: \(key))")
            return [:]
        }
        var progress: [String: Difficulty] = [:]
        saved.forEach { (wordId, difficultyTitle) in
            if let diff = Difficulty(title: difficultyTitle) {
                progress[wordId] = diff
            } else {
                print("⚠️ 無法解析儲存的難度 '\(difficultyTitle)' for wordId '\(wordId)'")
            }
        }
        print("✅ 已載入 \(URL(fileURLWithPath: filename).lastPathComponent) 的 Difficulty 進度")
        return progress
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

    private var currentFilenameForProgress: String?
    private var currentFileDisplayName: String? {
        didSet { title = currentFileDisplayName != nil ? "字卡: \(currentFileDisplayName!)" : "字卡複習" }
    }
    private var allCards: [Flashcard] = []
    private var learningQueue: [Flashcard] = []
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
        allCards.removeAll(); learningQueue.removeAll(); reviewPool.removeAll(); currentCard = nil
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
            let content = try String(contentsOf: url, encoding: .utf8)
            let filename = url.lastPathComponent; let displayName = url.deletingPathExtension().lastPathComponent
            if let oldFile = currentFilenameForProgress, !allCards.isEmpty { ProgressManager.shared.saveProgress(for: oldFile, cards: allCards) }
            cardLabel.text = ""; cardLabel.font = .systemFont(ofSize: 48, weight: .bold); translationLabel.isHidden = true
            let parsed = parseFlashcards(from: content, filenameForLogging: filename)
            if parsed.isEmpty {
                updateUIForNoFileLoaded(); currentFilenameForProgress = filename; currentFileDisplayName = displayName
                cardLabel.text = "檔案 \(filename)\n是空的或格式不正確。"; cardLabel.font = .systemFont(ofSize: 18); return
            }
            currentFilenameForProgress = filename; currentFileDisplayName = displayName
            let difficulties = ProgressManager.shared.loadProgress(for: filename)
            allCards = parsed.map { pCard in var card = pCard; if let diff = difficulties[card.id] { card.difficulty = diff }; return card }
            print("✅ 載入 \(filename)，共 \(allCards.count) 張。運行時複習狀態已重置。")
            learningQueue.removeAll(); reviewPool.removeAll(); fillReviewPool()
            navigationItem.rightBarButtonItem?.isEnabled = !allCards.isEmpty; loadNextCard()
        } catch { print("🚫 讀取檔案錯誤: \(error)"); updateUIForNoFileLoaded() }
    }
    func documentPickerWasCancelled(_ controller: UIDocumentPickerViewController) { print("ℹ️ 取消選擇") }

    private func fillReviewPool() {
        let currentSize = reviewPool.count + learningQueue.count
        if currentSize >= reviewPoolTargetSize && !reviewPool.isEmpty { return }
        let needed = reviewPoolTargetSize - currentSize; if needed <= 0 && !reviewPool.isEmpty { return }
        print("ℹ️ 填充複習池，需 \(max(0, needed))。 RP:\(reviewPool.count) LQ:\(learningQueue.count)")
        let existingIDs = Set(reviewPool.map{$0.id} + learningQueue.map{$0.id})
        let candidates = allCards.filter{!existingIDs.contains($0.id)}.sorted { c1,c2 in
            if c1.difficulty.weight != c2.difficulty.weight { return c1.difficulty.weight > c2.difficulty.weight }
            let c1Grad = (c1.difficulty == .easy && c1.consecutiveCorrectStreak >= graduatedThreshold)
            let c2Grad = (c2.difficulty == .easy && c2.consecutiveCorrectStreak >= graduatedThreshold)
            if c1Grad != c2Grad { return !c1Grad }
            if c1.reviewCount != c2.reviewCount { return c1.reviewCount < c2.reviewCount }
            if let d1=c1.lastReviewedDate, let d2=c2.lastReviewedDate { return d1 < d2 }
            return c1.lastReviewedDate == nil
        }
        reviewPool.append(contentsOf: candidates.prefix(max(0,needed))); reviewPool.shuffle()
        print("ℹ️ 填充後 RP: \(reviewPool.count)")
    }

    private func pickNextCard() -> Flashcard? {
        if !learningQueue.isEmpty { print("🎓 從 Learning Queue 取卡"); return learningQueue.removeFirst() }
        if reviewPool.isEmpty { fillReviewPool() }
        guard !reviewPool.isEmpty else {
            var didReset = false; print("ℹ️ Review Pool 為空，嘗試重置已畢業卡片...")
            for i in 0..<allCards.count {
                if allCards[i].difficulty == .easy && allCards[i].consecutiveCorrectStreak >= graduatedThreshold {
                    allCards[i].consecutiveCorrectStreak = 0; allCards[i].lastReviewedDate = nil; didReset = true
                    print("🔄 重置卡片: \(allCards[i].word)")
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
        if reviewPool.count + learningQueue.count < reviewPoolTargetSize / 2 && learningQueue.isEmpty { fillReviewPool() }
        if let next = pickNextCard() {
            currentCard = next; isShowingAnswer = false
            cardLabel.isHidden = false; translationLabel.isHidden = true
            cardLabel.text = next.word; translationLabel.text = next.translation
            flipButton.setTitle("顯示答案", for: .normal); flipButton.isHidden = false
            difficultyStack.arrangedSubviews.forEach { $0.isHidden = true }
            let graduatedCount = allCards.filter{ $0.difficulty == .easy && $0.consecutiveCorrectStreak >= graduatedThreshold }.count
            cardCountLabel.text = "學習中:\(learningQueue.count) | 待複習:\(reviewPool.count) | 已掌握:\(graduatedCount)"
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
              let filename = currentFilenameForProgress,
              let newDiff = Difficulty.allCases.first(where: {$0.weight == sender.tag}) else { return }
        var card = allCards[cardIdx]; let oldDiff = card.difficulty
        card.difficulty = newDiff; card.reviewCount += 1; card.lastReviewedDate = Date()
        let originalLQCount = learningQueue.count
        learningQueue.removeAll(where: {$0.id == card.id})
        if originalLQCount > learningQueue.count { print("ℹ️ \(card.word) 從 LQ 移除，因手動評分。") }
        card.timesInLearningQueue = 0
        switch newDiff {
        case .hard: card.consecutiveCorrectStreak = 0
            for _ in 0..<learningRepetitions { var lc = card; learningQueue.append(lc) }
            if learningRepetitions > 0 { learningQueue.shuffle() }
            print("🔴 \(card.word) 標為困難，加入 LQ (\(learningRepetitions)次)。LQ size: \(learningQueue.count)")
        case .medium: card.consecutiveCorrectStreak = (oldDiff == .easy || (oldDiff == .medium && newDiff == .medium)) ? card.consecutiveCorrectStreak + 1 : 1
            print("🟡 \(card.word) 標為中等，Streak:\(card.consecutiveCorrectStreak)")
        case .easy: card.consecutiveCorrectStreak += 1
            print("🟢 \(card.word) 標為簡單，Streak:\(card.consecutiveCorrectStreak)")
            if card.consecutiveCorrectStreak >= graduatedThreshold { print("🎉 \(card.word) 達到簡單畢業標準!") }
        }
        allCards[cardIdx] = card
        ProgressManager.shared.saveProgress(for: filename, cards: allCards)
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
