export const GRADES = [
  { id: 0, label: "Grade R", age: "5–6", emoji: "🌱", color: "#FF6B6B" },
  { id: 1, label: "Grade 1", age: "6–7", emoji: "⭐", color: "#FF8E53" },
  { id: 2, label: "Grade 2", age: "7–8", emoji: "🌟", color: "#FFC107" },
  { id: 3, label: "Grade 3", age: "8–9", emoji: "🚀", color: "#4CAF50" },
  { id: 4, label: "Grade 4", age: "9–10", emoji: "🔬", color: "#2196F3" },
  { id: 5, label: "Grade 5", age: "10–11", emoji: "💡", color: "#9C27B0" },
  { id: 6, label: "Grade 6", age: "11–12", emoji: "🌍", color: "#00BCD4" },
  { id: 7, label: "Grade 7", age: "12–13", emoji: "🎓", color: "#3F51B5" },
];

export const SUBJECTS = [
  { code: "MATH", label: "Mathematics", icon: "➗", color: "#FF6B6B" },
  { code: "ENG", label: "English", icon: "📚", color: "#4CAF50" },
  { code: "LIFE", label: "Life Skills", icon: "❤️", color: "#FF9800" },
  { code: "NS", label: "Natural Science", icon: "🔬", color: "#2196F3" },
  { code: "SS", label: "Social Sciences", icon: "🌍", color: "#9C27B0" },
];

export const AVATARS = ["🦁", "🐘", "🦒", "🦓", "🐆", "🦏", "🐬", "🦅", "🌺", "🌻", "⚡", "🌊"];

export const SA_THEMES = [
  "sharing food at a family braai",
  "buying sweets at a tuck shop",
  "counting animals on a game reserve",
  "travelling between SA cities",
];

export const QUESTION_BANK = {
  MATH: { 3: [
    { id:"q1", text:"Sipho cuts his pizza into 4 equal pieces and eats 1. What fraction did he eat?", story:"At the school tuck shop, Sipho buys a small pizza.", options:["1/2","1/4","1/3","4/1"], correct:1, difficulty:"Easy" },
    { id:"q2", text:"There are 12 apples. Ntombi takes half. How many does she take?", story:"Gogo has a fruit bowl with 12 apples on the stoep.", options:["4","6","8","3"], correct:1, difficulty:"Easy" },
    { id:"q3", text:"A chocolate bar has 8 pieces. Thabo eats 2/8. How many pieces?", story:"Thabo bought a Cadbury chocolate at the café.", options:["2","4","6","1"], correct:0, difficulty:"Medium" },
  ]},
  ENG: { 3: [
    { id:"q6", text:"Choose the correct spelling:", story:"Writing a story about animals on the veld.", options:["Elefant","Elephant","Elephent","Elifant"], correct:1, difficulty:"Easy" },
    { id:"q7", text:"Which word is a noun: 'The lion ran fast'?", story:"Reading about Kruger National Park.", options:["ran","fast","the","lion"], correct:3, difficulty:"Medium" },
  ]},
  LIFE: { 3: [{ id:"q8", text:"Ubuntu means:", story:"Teacher is teaching about SA values.", options:["I am strong","I am because we are","Work alone","Be the best"], correct:1, difficulty:"Easy" }]},
  NS: { 3: [{ id:"q9", text:"Which animal is a herbivore?", story:"On a game drive in the Kruger.", options:["Lion","Crocodile","Elephant","Shark"], correct:2, difficulty:"Easy" }]},
  SS: { 3: [{ id:"q10", text:"What is the seat-of-government capital of SA?", story:"Learning about our country.", options:["Cape Town","Johannesburg","Pretoria","Durban"], correct:2, difficulty:"Medium" }]},
};

export const SAMPLE_PLAN = {
  Mon:[{code:"MATH_FRAC",label:"Fractions",emoji:"➗",type:"gap-fill"},{code:"ENG_READ",label:"Reading",emoji:"📖",type:"grade-level"}],
  Tue:[{code:"LIFE_UBU",label:"Ubuntu",emoji:"❤️",type:"grade-level"},{code:"MATH_FRAC",label:"Fractions",emoji:"➗",type:"gap-fill"}],
  Wed:[{code:"NS_ANIM",label:"Animals",emoji:"🦁",type:"grade-level"}],
  Thu:[{code:"MATH_ADD",label:"Addition",emoji:"➕",type:"gap-fill"},{code:"SS_MAP",label:"SA Maps",emoji:"🌍",type:"grade-level"}],
  Fri:[{code:"ENG_SPELL",label:"Spelling",emoji:"✏️",type:"grade-level"}],
  Sat:[{code:"MATH_REV",label:"Maths Review",emoji:"⭐",type:"completed"}],
  Sun:[],
};

export const LESSON_TOPICS = {
  MATH:["Fractions","Addition & Subtraction","Multiplication","Geometry","Data Handling"],
  ENG:["Reading Comprehension","Creative Writing","Grammar & Spelling","Vocabulary","Oral Skills"],
  LIFE:["Ubuntu & Values","Personal Health","Environmental Awareness","Safety","Relationships"],
  NS:["Animals & Plants","Materials & Objects","Earth & Space","Energy & Change","Life & Living"],
  SS:["SA History","Geography of SA","Community & Society","Government & Democracy","Economy"],
};
