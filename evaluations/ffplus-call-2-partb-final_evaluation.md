# Evaluation Report: ffplus-call-2-partb-final.pdf

**Overall Score: 85.0/100**
- Panel Size: 3
- Criteria Source: evaluation_ffplus.pdf
- Date: 2026-02-07T20:04:03.513024+00:00

## Guidelines Compliance (45/46 passed)

| Status | Rule | Explanation |
|--------|------|-------------|
| PASS | Cover page must not be extended with any additional text/information | The cover page contains only the required information: call identifier, title, project details, innovation study title, coordinating person name and email, and the standard disclaimer text. |
| FAIL | Cover page format: Title First Name, Last Name, Partner Organisation | The coordinating person is listed as 'Yamaç Alican, Işık, Snowville Limited' which appears to follow the format, but 'Yamaç Alican' should be 'Yamaç' (first name) and 'Alican Işık' (last name), or the format is ambiguous. |
| PASS | Summary section should be approximately 0.5 pages | Section 1 (Summary) is approximately 0.5 pages as recommended. |
| PASS | Industrial relevance section should be approximately 3.5 pages | Section 2 (Industrial relevance, potential impact and exploitation plans) spans approximately 3.5 pages. |
| PASS | Description of work plan section should be approximately 5 pages | Section 3 (Description of the work plan) spans approximately 5-6 pages, meeting the recommendation. |
| PASS | Quality of consortium section should be approximately 2 pages | Section 4 (Quality of the consortium) spans approximately 2 pages. |
| PASS | Justification of costs section should be approximately 1 page | Section 5 (Justification of costs and resources) spans approximately 1-1.5 pages. |
| PASS | Main participant must be an SME or Start-up | Snowville Limited is identified as an EU-based SME in Section 2.1. |
| PASS | SME must have existing business model that benefits from generative AI development | Section 2.1 clearly describes Snowville's existing business developing safety-critical AI systems for airport operations and explains how generative AI capabilities are central to their business. |
| PASS | SME must demonstrate HPC awareness or experience | Section 2.1 explicitly states 'From a technical execution perspective, Snowville is HPC-ready' and describes their workflows designed for distributed training and HPC systems. |
| PASS | Clearly define the business problem | Section 2.2 clearly defines the business problem: 'ATC audio is not machine-actionable at scale' and explains the limitations of current approaches. |
| PASS | Explain how generative AI serves as solution to business problem | Section 2.2 explains how the generative audio-text model addresses the problem through joint modeling of speech, language, and operational semantics with structured decoding. |
| PASS | Explain why development of new model is imperative | Section 2.2 and 3.1 explain that existing general-purpose models fail on ATC communications and that the required combination of capabilities was not previously available. |
| PASS | Explain why this could not be addressed sooner | Section 2.2 states 'Until recently, the required combination of long-context generative architectures, large-scale ATC data, and stable HPC-enabled training workflows was not available.' |
| PASS | Explain expected business impact and value propositions | Section 2.3 comprehensively describes business impact, value propositions including three product directions, and the value creation process. |
| PASS | Define specific objectives for the innovation study | Section 3.1 lists four specific technical objectives (O1-O4) covering data preparation, model development, HPC improvements, and evaluation framework. |
| PASS | Provide detailed description and demonstrate availability of suitable training dataset | Section 3.2 provides comprehensive description of training data sources with Table 3-1 listing five datasets, their sizes, characteristics, and roles. All datasets are described as publicly available or licensed for research use. |
| PASS | Detail characteristics of models to be developed | Section 3.3 details the model architecture (audio-text transformer, 400M-1.5B parameters, extended context windows, structured decoding) and training strategy. |
| PASS | Outline repercussions of model characteristics to training and exploitation | Section 3.3 explains training requirements (long sequences, large batch sizes, curriculum learning) and Section 2.3 describes exploitation through three product directions. |
| PASS | Explain performance metrics | Section 3.3 under 'Experimentation Strategy' defines specific metrics: WER for transcription, accuracy and F1 for intent classification, precision/recall/F1 for entity grounding, and semantic consistency measures. |
| PASS | Describe benchmarks to establish baselines | Section 3.3 describes baseline performance using general-purpose ASR and ASR-based pipeline approaches evaluated on identical data splits. |
| PASS | Specify methods to ensure experiment reproducibility | Section 3.3 states 'Experiment reproducibility is ensured through fixed training, validation, and test partitions, controlled random seeds, and systematic tracking of model configurations.' |
| PASS | Identify potential risks considering EU guidelines for trustworthy AI | Section 3.4 addresses trustworthy AI considerations including mitigation of hallucination, bias evaluation across demographic factors, and alignment with EU trustworthy AI guidelines. |
| PASS | Include delivery of pre-final results and impact report by end of month 7 | Section 3.5 explicitly addresses the mandatory pre-final results report at Month 7, and Task 3 in Section 3.7 includes this deliverable. |
| PASS | Present a data management plan covering access, usage, sharing, retention, disposal, and FAIR principles | Section 3.6 provides a data management plan addressing data types, storage, security, licensing, and FAIR principles application. |
| PASS | Work plan must include task descriptions with duration, participants, deliverables, technical description, and computational resources | Section 3.7 provides three tasks (Task 1-3) each with duration, participants (Snowville with PM allocation), deliverables with months, technical descriptions, and computational resource specifications. |
| PASS | Specify total required CPU/GPU node hours | Section 3.7 under 'General information about Computational Resources' specifies 35,000-75,000 CPU node-hours and 60,000-110,000 GPU node-hours. |
| PASS | Provide information about EuroHPC JU access plans | Section 3.7 states 'Snowville plans to apply for EuroHPC JU access via the AI Factories access scheme in Month 1 of the project.' |
| PASS | If not using EuroHPC JU, explain alternative access to resources | Section 3.7 provides alternative arrangements: 'In case of access delays, equivalent nationally provisioned European HPC resources will be used. Commercial HPC may be employed as a contingency.' |
| PASS | Specify software requirements and data sets to be used | Section 3.7 describes software (containerised open-source frameworks, PyTorch, MPI, SLURM) and Section 5.1 provides additional details. Data sets are described in Section 3.2. |
| PASS | Describe outputs and results/impact of the innovation study | Section 3.7 'Impact and Outputs' clearly lists outputs (trained model, dataset, evaluation framework, reports) and results (demonstrated improvements, strengthened capabilities, validated foundation). |
| PASS | Provide participant effort table with person-months | Section 3.7 includes a table showing Snowville with 15 PM total effort. |
| PASS | Maximum of one main participant (SME/Start-up) and up to two supporting participants | The proposal has only one participant (Snowville, the main SME participant), which is within the limit. |
| PASS | Each consortium partner must have clearly defined role | Section 3.7 and 4.1 clearly define Snowville's role as the sole SME participant responsible for all technical activities. |
| PASS | Explain each proposer's capability as organization and key staff | Section 4.1 describes Snowville's organizational capabilities, and Section 4.2 provides detailed profiles of two key staff members with their specific roles and qualifications. |
| PASS | SME must have qualified staff with expertise in generative AI, software development, technical project management, and data processing | Section 4.1 lists in-house capabilities including generative AI, deep learning, data engineering, HPC-scale training, and safety-critical evaluation. Section 4.2 profiles staff with relevant expertise. |
| PASS | For supporting participants, only technical/engineering activities are eligible | Not applicable - there are no supporting participants in this proposal. |
| PASS | Clearly explain HPC resources needed (hardware, software, frameworks, compute volumes) | Section 5.1 explains HPC requirements: 60,000-110,000 GPU node-hours, 35,000-70,000 CPU node-hours, high-memory GPUs (80GB), high-bandwidth interconnects, and software stack details. |
| PASS | Define if using EuroHPC JU resources (e.g., AI Factories Access Modes) | Section 5.1 states plans to use AI Factories Fast-Lane and Large-Scale access modes, and Section 3.7 mentions applying in Month 1. |
| PASS | Demonstrate how allocated resources address gaps in processes | Section 5.1 under 'Personnel Resources' explains that allocated effort addresses capability gaps in HPC-scale experimentation, multi-node training optimization, and domain-specific evaluation that cannot be absorbed in existing workloads. |
| PASS | Provide cost breakdown table with personnel costs, other direct costs, and requested funding per participant | Section 5.2 includes a complete cost breakdown table showing Snowville with 15 PM, €180,000 personnel costs, €12,500 other direct costs, total €192,500 at 100% funding rate. |
| PASS | All other direct costs must be clearly explained and justified | Section 5.2 under 'Other Direct Costs' breaks down the €12,500 into targeted data annotation (€5,000) and aviation-specific dataset licensing (€7,500) with clear justification. |
| PASS | Computing costs should be included in other direct costs if applicable | Section 5.2 explicitly states 'No HPC compute costs are included under Other Direct Costs' because resources will be accessed via EuroHPC JU free of charge. |
| PASS | Indirect costs are not eligible for innovation study participants | The cost table in Section 5.2 does not include any indirect costs, complying with this rule. |
| PASS | Proposal must target innovation studies using large-scale European HPC resources | The entire proposal is designed around using large-scale European HPC resources, with detailed justification in Sections 3.3, 3.7, and 5.1 explaining why HPC is necessary. |
| PASS | Innovation studies must develop and customize generative AI models | The proposal focuses on developing a domain-specialized generative audio-text model with customized decoder architecture for ATC communications, as described throughout Section 3. |

## Score Summary

| Criterion | Median | Mean | Std Dev | Weight |
|-----------|--------|------|---------|--------|
| Excellence | 82 | 82 | 0.0 | 33% |
| Impact | 85 | 86 | 1.7 | 33% |
| Implementation | 88 | 87 | 1.7 | 33% |

## Excellence — 82/100 (agreement: High)

### Suggestions for Improvement
- Provide explicit justification for model size selection criteria and expected performance-compute tradeoffs across the 400M-1.5B parameter range
- Define specific hyperparameter ranges for key architectural choices (number of layers, attention heads, context window selection rationale) with preliminary ablation study plans
- Name specific experiment tracking tools (e.g., MLflow, Weights & Biases self-hosted) and version control strategies to strengthen reproducibility claims
- Add a dedicated risk register table identifying technical risks (training instability, multi-task optimization challenges, data imbalance) with specific mitigation strategies and contingency plans
- Define quantitative thresholds for acceptable hallucination rates and entity grounding errors in safety-critical contexts
- Include preliminary strategy for monitoring model drift during exploitation phase, even though deployment is out of scope for this study
- Specify which baseline ASR models will be used (e.g., Whisper, specific versions) to enable reproducible comparison
- Add specific risk mitigation table with technical risks (e.g., convergence failure, memory overflow, data quality issues) and concrete contingency actions
- Provide ablation study plan showing how model size will be systematically determined (e.g., 400M baseline, then 800M, then 1.5B with performance/cost tradeoffs)
- Specify exact baseline model versions (e.g., 'Whisper-large-v3' or specific ASR system) and define minimum acceptable performance improvements (e.g., '15% relative WER reduction')
- Detail the abstention mechanism: confidence thresholds, uncertainty estimation method, and expected abstention rates on test sets
- Add brief section on post-deployment monitoring strategy even if out of scope for this study, showing awareness of operational considerations
- Describe annotation quality assurance process including inter-annotator agreement targets, expert review protocols, and conflict resolution procedures
- Add an explicit risk register table identifying technical risks (e.g., training instability, data quality issues, HPC access delays) with likelihood, impact, and specific mitigation actions
- Provide more detail on training hyperparameters and optimization strategy, including learning rate schedules, warmup strategies, gradient clipping, and multi-task loss weighting approaches
- Expand benchmarking to include comparison with state-of-the-art audio-language models (e.g., Whisper variants, recent speech-text transformers) and any existing ATC-specific models in literature
- Elaborate on model drift mitigation with specific monitoring metrics and retraining triggers that would be implemented in operational deployment
- Specify convergence criteria and validation thresholds for transitioning between training stages to make the curriculum learning strategy more reproducible

## Impact — 85/100 (agreement: High)

### Suggestions for Improvement
- Add quantitative business metrics: current annual revenue range, number of existing customers/pilots, projected revenue impact within 12-24 months post-study
- Include brief competitive analysis positioning Snowville's approach against existing ATC analytics providers and general-purpose AI solutions
- Develop explicit commercialization timeline showing path from Month 10 study completion to product integration, pilot deployments, and revenue generation
- Provide order-of-magnitude market sizing for European airport/ANSP market and addressable segment for each product direction
- Quantify expected energy efficiency gains from HPC-optimized training compared to iterative cloud-based approaches to strengthen environmental impact narrative
- Articulate IP strategy for model architecture innovations and data curation methodologies developed during the study
- Define 2-3 specific KPIs that will be tracked in Month 7 impact assessment to demonstrate business trajectory (e.g., customer pilot commitments, integration milestones)
- Add business metrics section with: current annual revenue range, number of existing customers/pilots, total addressable market size for ATC solutions, and specific revenue targets post-study
- Define business success criteria for Month 7 report: e.g., 'technical performance sufficient to initiate pilot with 2 European airports by Month 12' or 'secure €X in follow-on funding'
- Include 12-18 month commercialization roadmap showing path from validated model to paying customers, including regulatory considerations for safety-critical aviation systems
- Add competitive analysis paragraph identifying key competitors and Snowville's differentiation (domain specialization, European data sovereignty, HPC-enabled scale)
- Strengthen customer validation with specific partner names (if permitted) or at minimum quantify engagement: 'letters of intent from X airports representing Y annual passengers'
- Add brief environmental impact statement: estimated energy consumption for training vs. expected operational efficiency gains or safety improvements
- Clarify company stage and provide appropriate context: if established SME, show revenue trajectory; if start-up, explain funding status and investor validation
- Add quantitative business projections: target revenue within 2-3 years post-study, number of prospective customers in pipeline, estimated market size for ATC intelligence solutions in Europe
- Provide more detail on commercialization strategy: customer segments, pricing model (SaaS, licensing, integration fees), sales approach, and timeline from study completion to first commercial deployment
- Include evidence of customer validation: letters of interest from airports/ANSPs, pilot project agreements, or advisory board involvement to demonstrate market pull
- Add competitive analysis section identifying existing ATC transcription/analysis vendors and clearly articulating Snowville's differentiation and barriers to entry
- Quantify environmental impact: estimate energy consumption for training vs. inference, compare HPC efficiency to cloud alternatives, discuss operational efficiency gains that reduce aviation carbon footprint
- Strengthen success story potential by committing to specific dissemination activities: conference presentations, technical publications, or case studies with named airport partners

## Implementation — 88/100 (agreement: High)

### Suggestions for Improvement
- Add Gantt chart or timeline diagram showing task dependencies and parallel work streams, particularly clarifying how Task 1 base encoder selection feeds into Task 2
- Develop detailed HPC access contingency timeline: if EuroHPC access delayed, specify trigger points (e.g., Month 2 decision point) for activating national HPC or commercial alternatives
- Specify FTE commitments for key personnel: e.g., 'Yamaç Alican Işık: 0.8 FTE Months 2-6, 0.4 FTE Months 1,7-10' to demonstrate feasibility of 15 PM with 2-person team
- Add brief project management section describing: weekly progress tracking, monthly milestone reviews, decision protocols for model architecture selection, and escalation procedures
- Quantify HPC access risk impact: 'Each month of access delay reduces training iterations by ~30%, with fallback to smaller model (400M) if access delayed beyond Month 4'
- Create explicit data sharing matrix specifying which artifacts (model checkpoints, evaluation datasets, synthetic data) will be openly released vs. access-controlled with justification
- Define quality gates at key milestones (e.g., Task 1 completion requires documented baseline results before Task 2 full-scale training begins)
- Add explicit statement that no supporting participants are included since single-participant consortium covers all required competencies
- Specify backup HPC systems by name (e.g., 'LUMI, MareNostrum5, or Leonardo') and allocate €10-15k contingency budget for commercial HPC if EuroHPC access delayed beyond Month 2
- Add Gantt chart showing task timelines, milestones, and dependencies - clarify Month 2-3 overlap between Task 1 and Task 2 (likely encoder selection feeding into training start)
- Create personnel allocation matrix: map 15 PM across tasks and roles (e.g., 'CTO: 10 PM total - 2 PM Task 1, 6 PM Task 2, 2 PM Task 3; CEO: 5 PM total...')
- Expand data management plan: specify 5-year retention for training data, 10-year for model checkpoints, use Git-LFS for versioning, document disposal via secure deletion protocols
- Add quality assurance section: peer review of code by both team members, external ATC expert validation of entity annotations, reproducibility checks via independent re-runs
- Clarify procurement: state whether annotation/licensing are direct purchases or subcontracts, ensure compliance with FFplus subcontracting limits if applicable
- Define HPC performance targets: 'Achieve >70% scaling efficiency on 4 nodes, >50% on 8 nodes for 1.5B parameter model' with plan to measure and report in Month-7 assessment
- Add risk register table: list top 5 implementation risks (HPC access delay, data quality issues, convergence problems, personnel availability, licensing delays) with mitigation and owner
- Add a visual work plan (Gantt chart) showing task timelines, dependencies, and critical path, with key milestones and decision points clearly marked
- Specify concrete HPC access contingency triggers: e.g., 'if EuroHPC access not secured by Month 2, activate national HPC option; if delayed beyond Month 3, use commercial HPC with internal funds'
- Enhance data management plan with specific retention periods (e.g., raw audio: 5 years, model checkpoints: 3 years) and clarify which derived datasets will be released publicly to maximize FAIR compliance
- Formalize operational validation partnerships: add letters of support from airports/ANSPs or specify advisory board structure to ensure aviation domain expertise is systematically incorporated
- Provide refined compute estimates with breakdown by training stage: e.g., 'Stage 1 (weak supervision): 20-30k GPU hours; Stage 2 (structured decoding): 30-50k GPU hours; Stage 3 (robustness): 10-30k GPU hours'
- Define quantitative success thresholds for Month 7 assessment: e.g., 'WER <15% on noisy test set, intent classification F1 >0.85, entity grounding F1 >0.80, demonstrating >20% relative improvement over pipeline baseline'

## Individual Reviewer Scores

| Reviewer | Excellence | Impact | Implementation | Overall |
|----------|--------|--------|--------|---------|
| #1 | 82 | 88 | 85 | 85.0 |
| #2 | 82 | 85 | 88 | 85.0 |
| #3 | 82 | 85 | 88 | 85.0 |
