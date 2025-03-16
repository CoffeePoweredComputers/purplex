<template>
  <div class="publications-list">
    <h1 class="title">About</h1>
    <p>
      This tool is a research project that supports the continued development and evaluation of of natural language programming activites that aim to support the skills needed for students to successfully engage in Human-GenAI collaborative coding. Research surrounding the development of this tool has been published is detailed below and organized by topic.
    </p>
    <div class="scholar-link">
      This tool was developed by <a href="https://scholar.google.com/citations?user=hpe-z9YAAAAJ" target="_blank" style="color: white; text-decoration: underline;">David H. Smith IV</a>
    </div>
    <h2 class="title">Code Generation Grading</h2>
    
    <ul class="publications">
      <li v-for="(paper, index) in publications" :key="index" class="publication-item">
        <span class="publication-title">{{ paper.title }}</span>
        <span class="publication-meta">{{ paper.authors }} | {{ paper.venue }} ({{ paper.year }})</span>
        <span class="publication-actions">
          <button class="btn"><a v-if="paper.url" :href="paper.url" target="_blank">View</a></button> | 
          <button @click="copyBibTeX(paper.bibtex)" class="btn">Copy BibTeX</button>
          <span v-show="paper.showCopied" class="copied-message">✓</span>
        </span>
      </li>
    </ul>
  </div>
</template>

<script>
import { reactive } from 'vue';

export default {
  name: 'About',
  setup() {
    const publications = reactive([
      {
        title: "Code Generation Based Grading: Evaluating an Auto-grading Mechanism for 'Explain-in-Plain-English' Questions",
        authors: "DH Smith IV and C Zilles",
        venue: "ACM ITiCSE",
        year: 2024,
        url: "https://dl.acm.org/doi/abs/10.1145/3649217.3653582",
        showCopied: false,
        bibtex: `@incollection{smith2024code,
  title={Code Generation Based Grading: Evaluating an Auto-grading Mechanism for" Explain-in-Plain-English" Questions},
  author={Smith IV, David H and Zilles, Craig},
  booktitle={Proceedings of the 2024 on Innovation and Technology in Computer Science Education V. 1},
  pages={171--177},
  year={2024}
}`
      },
      {
        title: "Prompting for Comprehension: Exploring the Intersection of Explain in Plain English Questions and Prompt Writing",
        authors: "DH Smith IV, P Denny, M Fowler, and C Zilles",
        venue: "ACM Learning@Scale",
        year: 2024,
        url: "https://dl.acm.org/doi/pdf/10.1145/3657604.3662039",
        showCopied: false,
        bibtex: `@inproceedings{smith2024prompting,
  title={Prompting for comprehension: Exploring the intersection of explain in plain english questions and prompt writing},
  author={Smith IV, David H and Denny, Paul and Fowler, Max},
  booktitle={Proceedings of the Eleventh ACM Conference on Learning@ Scale},
  pages={39--50},
  year={2024}
}`
      },
      {
        title: "Integrating Natural Language Prompting Tasks in Introductory Programming Courses",
        authors: "C Kerslake, P Denny, DH Smith IV, J Prather, J Leinonen, A Luxton-Reilly, S MacNeil",
        venue: "ACM SIGCSE Virtual",
        year: 2024,
        url: "https://dl.acm.org/doi/pdf/10.1145/3657604.3662039",
        showCopied: false,
        bibtex: `@inproceedings{smith2024prompting,
  title={Prompting for comprehension: Exploring the intersection of explain in plain english questions and prompt writing},
  author={Smith IV, David H and Denny, Paul and Fowler, Max},
  booktitle={Proceedings of the Eleventh ACM Conference on Learning@ Scale},
  pages={39--50},
  year={2024}
}`
      },
      {
        title: "Explain in Plain Language Questions with Indic Languages: Drawbacks, Affordances, and Opportunities",
        authors: "DH Smith IV, V Kumar, P Denny",
        venue: "ACM India: COMPUTE 2024",
        year: 2024,
        url: "https://arxiv.org/pdf/2409.20297",
        showCopied: false,
        bibtex: `@article{smith2024explain,
  title={Explain in Plain Language Questions with Indic Languages: Drawbacks, Affordances, and Opportunities},
  author={Smith IV, David H and Kumar, Viraj and Denny, Paul},
  journal={arXiv preprint arXiv:2409.20297},
  year={2024}
}`
      }
    ]);

    const copyBibTeX = (bibtex) => {
      navigator.clipboard.writeText(bibtex);
      
      // Reset all copied messages
      publications.forEach(paper => {
        paper.showCopied = false;
      });
      
      // Find the paper that was copied and show its message
      const paper = publications.find(p => p.bibtex === bibtex);
      if (paper) {
        paper.showCopied = true;
        setTimeout(() => {
          paper.showCopied = false;
        }, 2000);
      }
    };

    return {
      publications,
      copyBibTeX
    };
  }
};
</script>

<style scoped>
.publications-list {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  font-family: Arial, sans-serif;
}

.title {
  margin-bottom: 10px;
}

.scholar-link {
  margin-bottom: 20px;
}

.scholar-link a {
  color: #1a0dab;
  text-decoration: none;
}

.scholar-link a:hover {
  text-decoration: underline;
}

.publications {
  list-style-type: none;
  padding: 0;
  margin: 0;
}

.publication-item {
  padding: 12px 0;
  border-bottom: 1px solid #eee;
}

.publication-title {
  font-weight: bold;
  display: block;
  margin-bottom: 5px;
}

.publication-meta {
  color: #555;
  font-size: 0.9em;
  display: block;
  margin-bottom: 5px;
}

.publication-actions {
  font-size: 0.9em;
  display: block;
}

.publication-actions a {
  color: #1a0dab;
  text-decoration: none;
}

.publication-actions a:hover {
  text-decoration: underline;
}

.btn, .btn a
  {
  background: purple;
  border: none;
  color: white;
  font-weight: bold;
  cursor: pointer;
  font-size: 1em;
  padding: 2px 5px 2px 5px;
  font-family: inherit;
  text-align: center;
}

.btn:hover {
  text-decoration: underline;
}

.copied-message {
  color: green;
  margin-left: 5px;
}
</style>
