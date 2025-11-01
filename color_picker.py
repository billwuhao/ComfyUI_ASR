class ColorPickerMW:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "color": ("COLORHEX", {"default": "#f30e0eff"}), 
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("#RRGGBB",)
    FUNCTION = "pick_color"
    CATEGORY = "🎤MW/MW-ASR"

    def pick_color(self, color):
        return (color,) 
