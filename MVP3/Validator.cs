using System.Text.Json;

namespace Mvp3;

public static class Validator
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
    };

    public static void Run(string rootDirectory, string inputPath, string modelPath,
        string outputDirectory, bool allowResize)
    {
        Directory.CreateDirectory(outputDirectory);
        SparseDctModel model = Applicator.LoadModel(modelPath);
        ImageData original = ImageIo.Load(inputPath);

        bool wrongSizeRejected = false;
        if (original.Width != model.Width || original.Height != model.Height)
        {
            try
            {
                _ = Applicator.Apply(original, model, false);
            }
            catch (InvalidDataException)
            {
                wrongSizeRejected = true;
            }
            if (!allowResize)
                throw new InvalidDataException("Validation input has the wrong dimensions; pass --resize.");
        }
        else
        {
            wrongSizeRejected = true; // Not applicable; strict path already has the required size.
        }

        ImageData normalized = original.Width == model.Width && original.Height == model.Height
            ? original : ImageIo.Resize(original, model.Width, model.Height);
        ImageData output = Applicator.Apply(original, model, allowResize);
        string outputPath = Path.Combine(outputDirectory, "test_output.png");
        ImageIo.SaveRgbaPng(outputPath, output);

        byte[] learned = DctModel.ReconstructBytes(model);
        int contentPixels = 0;
        int exteriorPixels = 0;
        int rgbMismatches = 0;
        int alphaMismatches = 0;
        for (int p = 0; p < learned.Length; p++)
        {
            int i = p * 4;
            if (learned[p] >= model.ContentThreshold)
            {
                contentPixels++;
                if (output.Pixels[i] != normalized.Pixels[i] ||
                    output.Pixels[i + 1] != normalized.Pixels[i + 1] ||
                    output.Pixels[i + 2] != normalized.Pixels[i + 2])
                    rgbMismatches++;
                byte expected = (byte)((normalized.Pixels[i + 3] * learned[p] + 127) / 255);
                if (output.Pixels[i + 3] != expected)
                    alphaMismatches++;
            }
            else
            {
                exteriorPixels++;
                if (output.Pixels[i] != 0 || output.Pixels[i + 1] != 0 || output.Pixels[i + 2] != 0)
                    rgbMismatches++;
                if (output.Pixels[i + 3] != learned[p])
                    alphaMismatches++;
            }
        }
