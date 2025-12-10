import Logo from "@/components/logo";
import { GITHUB_REPO_URL } from "@/constants/config";
import { Github } from "@/constants/icons";
import type { BaseLayoutProps } from "fumadocs-ui/layouts/shared";


export const baseOptions: BaseLayoutProps = {
  nav: {
    title: <Logo />,
  },
  links: [
    {
      type: "menu",
      text: "Guide",
      items: [
        {
          text: "Getting Started",
          description: "Learn to use Chainless",
          url: "/docs",
        },
      ],
    },
    {
      type: "menu",
      text: "Community",
      items: [
        {
          text: "GitHub Discussions",
          description: "Ask questions or start discussions",
          url: `${GITHUB_REPO_URL}/discussions`,
        },
        {
          text: "Issues",
          description: "Report bugs or request features",
          url: `${GITHUB_REPO_URL}/issues`,
        },
      ],
    },
    {
      type: "menu",
      text: "About",
      items: [
        {
          text: "What is Chainless?",
          description: "The motivation, philosophy, and purpose behind the Chainless framework.",
          url: "/docs/what-is-chainless",
        },
        {
          text: "Contributing",
          description: "How to contribute to Chainless",
          url: "/docs/contributing",
        }
      ],
    },

    {
      type: "icon",
      label: "Github",
      icon: <Github />,
      text: "Github",
      url: GITHUB_REPO_URL,
    },
  ],
};
