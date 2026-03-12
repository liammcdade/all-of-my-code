import random
import textwrap

class PromptEnhancer:
    """
    A comprehensive prompt enhancer for generating high-quality prompts for AI models like ChatGPT.

    Features:
    - Multiple enhancement categories (mood, setting, style, complexity)
    - Template-based generation
    - Configurable output length and detail level
    - Batch generation of multiple prompt variations
    """

    def __init__(self):
        # Define comprehensive enhancement categories
        self.mood_adjectives = [
            "majestic", "ethereal", "vibrant", "serene", "intense", "mystical",
            "radiant", "thought-provoking", "captivating", "profound", "innovative"
        ]

        self.setting_descriptors = [
            "in an otherworldly landscape", "amidst cosmic wonders", "in a futuristic metropolis",
            "within an ancient mystical realm", "in a vibrant underwater world", "on a desolate alien planet",
            "in a bustling Victorian-era city", "in the depths of a dense forest", "in zero gravity",
            "in a parallel dimension", "in a dreamlike state"
        ]

        self.style_elements = [
            "with unparalleled clarity and precision", "through a lens of wonder", "embracing innovation",
            "with meticulous attention to detail", "featuring intricate relationships",
            "showcasing dynamic interactions", "exploring profound concepts", "with striking visuals"
        ]

        self.complexity_templates = [
            "Develop a comprehensive {topic} that {details}",
            "Create an in-depth exploration of {topic}, focusing on {details}",
            "Design a detailed framework for {topic} that incorporates {details}",
            "Build a sophisticated system for {topic} {details}"
        ]

        self.perspective_modifiers = [
            "from multiple vantage points", "through diverse perspectives", "with unique insights",
            "considering various facets", "embracing holistic understanding"
        ]

    def enhance_prompt(self, base_prompt, mood=True, setting=True, style=True, complexity=True,
                      custom_elements=None, detail_level="medium"):
        """
        Enhance a prompt with configurable elements.

        Args:
            base_prompt (str): The original prompt to enhance
            mood (bool): Include mood adjectives
            setting (bool): Add setting descriptors
            style (bool): Incorporate style elements
            complexity (bool): Use complexity templates
            custom_elements (list): Additional custom elements to include
            detail_level (str): "low", "medium", or "high" for output verbosity

        Returns:
            str: Enhanced prompt
        """
        enhanced_parts = []

        if mood:
            enhanced_parts.append(random.choice(self.mood_adjectives))

        # Keep the base prompt as core element
        enhanced_parts.append(base_prompt.lower().strip())

        if complexity and random.random() > 0.5:
            template = random.choice(self.complexity_templates)
            enhanced_parts = [template.format(
                topic=" ".join(enhanced_parts),
                details=random.choice(self.perspective_modifiers)
            )]

        if setting:
            enhanced_parts.append(random.choice(self.setting_descriptors))

        if style:
            enhanced_parts.append(random.choice(self.style_elements))

        if custom_elements:
            # Add random selection of custom elements
            enhanced_parts.extend(random.sample(custom_elements, min(2, len(custom_elements))))

        # Join and format the enhanced prompt
        enhanced_prompt = " ".join(enhanced_parts)

        # Capitalize first letter
        enhanced_prompt = enhanced_prompt[0].upper() + enhanced_prompt[1:]

        # Add period if it doesn't end with punctuation
        if not enhanced_prompt.endswith(('.', '!', '?', ':')):
            enhanced_prompt += '.'

        return enhanced_prompt

    def generate_multiple_prompts(self, base_prompt, count=5, detail_level="medium", **kwargs):
        """
        Generate multiple enhanced prompt variations.

        Args:
            base_prompt (str): Original prompt
            count (int): Number of variations to generate
            detail_level (str): Detail level for each prompt
            **kwargs: Enhancement options

        Returns:
            list: List of enhanced prompts
        """
        prompts = []
        for _ in range(count):
            prompt = self.enhance_prompt(base_prompt, detail_level=detail_level, **kwargs)
            # Ensure uniqueness by avoiding exact duplicates
            while prompt in prompts:
                prompt = self.enhance_prompt(base_prompt, detail_level=detail_level, **kwargs)
            prompts.append(prompt)
        return prompts

    def analyze_prompt_quality(self, prompt):
        """
        Analyze the quality of an enhanced prompt.

        Args:
            prompt (str): Prompt to analyze

        Returns:
            dict: Quality metrics
        """
        metrics = {
            "word_count": len(prompt.split()),
            "sentence_count": len([s for s in prompt.split('.') if s.strip()]),
            "unique_words": len(set(prompt.lower().split())),
            "adjectives_count": sum(1 for word in prompt.lower().split() if word in [
                adj.lower() for adj in self.mood_adjectives + self.style_elements
            ]),
            "has_setting": any(setting.lower() in prompt.lower() for setting in self.setting_descriptors),
        }
        return metrics

def enhance_prompt(prompt):
    """
    Legacy function for backward compatibility.
    """
    enhancer = PromptEnhancer()
    return enhancer.enhance_prompt(prompt)

if __name__ == "__main__":
    import sys

    enhancer = PromptEnhancer()

    # Get prompt from command line argument or stdin
    if len(sys.argv) > 1:
        user_prompt = " ".join(sys.argv[1:]).strip()
    else:
        user_prompt = input("Enter your prompt: ").strip()

    if not user_prompt:
        print("Please provide a prompt.")
        sys.exit(1)

    # Generate and output a single enhanced prompt
    enhanced = enhancer.enhance_prompt(user_prompt)
    print(enhanced)
