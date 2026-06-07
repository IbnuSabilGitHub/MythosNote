/**
 * Handle interactive quiz interface
 */

document.addEventListener("DOMContentLoaded", () => {
    const dataNode = document.getElementById("quiz-data");
    if (!dataNode) return;

    let quizData = null;
    try {
        let rawData = dataNode.textContent.trim();
        // Remove markdown fencing if it exists
        if (rawData.startsWith("```json")) {
            rawData = rawData.replace(/^```json\n/, "").replace(/\n```$/, "");
        } else if (rawData.startsWith("```")) {
            rawData = rawData.replace(/^```\n/, "").replace(/\n```$/, "");
        }
        quizData = JSON.parse(rawData);
        // Handle double-encoded JSON: json_script on a string yields a JSON string
        if (typeof quizData === "string") {
            quizData = JSON.parse(quizData);
        }
    } catch (err) {
        console.error("Failed to parse quiz data:", err);
        document.getElementById("quiz-question-text").textContent = "Gagal memuat data kuis.";
        return;
    }

    const questions = quizData.questions || [];
    if (questions.length === 0) {
        document.getElementById("quiz-question-text").textContent = "Tidak ada pertanyaan.";
        return;
    }

    let currentIndex = 0;
    // Store user answers: userAnswers[index] = { selectedOption, isCorrect }
    const userAnswers = new Array(questions.length).fill(null);

    // DOM Elements
    const progressText = document.getElementById("quiz-progress-text");
    const progressPercent = document.getElementById("quiz-progress-percent");
    const progressBar = document.getElementById("quiz-progress-bar");
    const questionText = document.getElementById("quiz-question-text");
    const optionsContainer = document.getElementById("quiz-options-container");
    const explanationBlock = document.getElementById("quiz-explanation-block");
    const explanationText = document.getElementById("quiz-explanation-text");
    
    const quizCard = document.getElementById("quiz-card");
    const endScreen = document.getElementById("quiz-end-screen");
    const scoreText = document.getElementById("quiz-score-text");
    const controls = document.getElementById("quiz-controls");
    
    const btnPrev = document.getElementById("btn-prev");
    const btnNext = document.getElementById("btn-next");

    function renderQuestion(index) {
        const q = questions[index];
        const state = userAnswers[index];
        const hasAnswered = state !== null;

        // Update Progress
        progressText.textContent = `Pertanyaan ${index + 1} dari ${questions.length}`;
        const pct = Math.round(((index + 1) / questions.length) * 100);
        progressPercent.textContent = `${pct}%`;
        progressBar.style.width = `${pct}%`;

        // Update Text
        questionText.textContent = q.question;
        
        // Update Options
        optionsContainer.innerHTML = "";
        
        const answerRegex = /^([A-D])\./i;
        let correctAnswerLetter = "A";
        if (q.answer) {
            const match = q.answer.match(answerRegex);
            if (match) correctAnswerLetter = match[1].toUpperCase();
            else if (q.answer.length === 1) correctAnswerLetter = q.answer.toUpperCase();
        }

        q.options.forEach((opt, optIdx) => {
            const letter = String.fromCharCode(65 + optIdx); // A, B, C, D
            const isCorrectOption = letter === correctAnswerLetter;
            
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "w-full text-left p-4 rounded-lg border flex items-center gap-4 transition-all duration-200 group";
            
            // Default styles
            let borderClass = "border-stone-800 bg-neutral-900";
            let circleClass = "border-stone-600 bg-transparent";
            let circleContent = "";
            let textClass = "text-stone-300";

            if (hasAnswered) {
                btn.disabled = true;
                btn.classList.add("cursor-default");
                
                if (state.selectedOption === letter) {
                    // This is what the user clicked
                    if (state.isCorrect) {
                        borderClass = "border-green-600 bg-green-900/10";
                        circleClass = "border-green-500 bg-green-500";
                        circleContent = `<iconify-icon icon="tabler:check" class="text-white text-xs"></iconify-icon>`;
                        textClass = "text-zinc-100 font-medium";
                    } else {
                        borderClass = "border-red-600/50 bg-red-900/10";
                        circleClass = "border-red-500/50 bg-red-500/50";
                        circleContent = `<iconify-icon icon="tabler:x" class="text-white text-xs"></iconify-icon>`;
                        textClass = "text-stone-400";
                    }
                } else if (isCorrectOption) {
                    // This was the correct one but user didn't click it
                    borderClass = "border-green-600/50 bg-neutral-900";
                    circleClass = "border-green-500 bg-green-500";
                    circleContent = `<iconify-icon icon="tabler:check" class="text-white text-xs"></iconify-icon>`;
                    textClass = "text-zinc-200";
                }
            } else {
                // Interactive styles
                borderClass += " hover:border-primary/50 hover:bg-neutral-800";
                btn.addEventListener("click", () => handleSelectOption(letter, isCorrectOption));
            }

            btn.classList.add(...borderClass.split(" "));

            const circle = document.createElement("div");
            circle.className = `w-5 h-5 rounded-full border flex justify-center items-center shrink-0 transition-colors ${circleClass}`;
            if (!hasAnswered) {
                circle.classList.add("group-hover:border-primary/50");
            }
            circle.innerHTML = circleContent;

            const textSpan = document.createElement("span");
            textSpan.className = `text-sm leading-relaxed ${textClass}`;
            // If the option already starts with "A. ", remove it for cleaner display
            textSpan.textContent = opt.replace(/^[A-D]\.\s*/i, "");

            // Label for option (A, B, C, D)
            const labelSpan = document.createElement("span");
            labelSpan.className = "text-xs font-bold text-stone-500 w-4 shrink-0";
            labelSpan.textContent = letter;

            btn.appendChild(circle);
            btn.appendChild(labelSpan);
            btn.appendChild(textSpan);

            optionsContainer.appendChild(btn);
        });

        // Update Explanation
        if (hasAnswered && q.explanation) {
            explanationBlock.classList.remove("hidden");
            explanationText.textContent = q.explanation;
        } else {
            explanationBlock.classList.add("hidden");
        }

        // Update Nav Buttons
        btnPrev.disabled = index === 0;
        
        if (hasAnswered) {
            if (index === questions.length - 1) {
                btnNext.textContent = "Selesaikan Kuis";
                btnNext.onclick = showEndScreen;
            } else {
                btnNext.textContent = "Pertanyaan Berikutnya";
                btnNext.onclick = () => { currentIndex++; renderQuestion(currentIndex); };
            }
            btnNext.disabled = false;
        } else {
            btnNext.textContent = "Cek Jawaban";
            btnNext.disabled = true; // Wait for selection
        }
    }

    function handleSelectOption(letter, isCorrect) {
        userAnswers[currentIndex] = {
            selectedOption: letter,
            isCorrect: isCorrect
        };
        renderQuestion(currentIndex);
    }

    function showEndScreen() {
        quizCard.classList.add("hidden");
        controls.classList.add("hidden");
        endScreen.classList.remove("hidden");
        endScreen.classList.add("flex");

        const correctCount = userAnswers.filter(a => a && a.isCorrect).length;
        scoreText.textContent = `Skor Anda ${correctCount} dari ${questions.length}.`;
    }

    btnPrev.addEventListener("click", () => {
        if (currentIndex > 0) {
            currentIndex--;
            renderQuestion(currentIndex);
        }
    });

    // Initial render
    renderQuestion(currentIndex);
});
