# Homebrew formula for deslopper, kept here as the source of truth.
#
# The live copy is Formula/deslopper.rb in the jv-k/homebrew-tap repo. At each release,
# release.yml points its `url` and `sha256` at the sdist attached to the GitHub release
# (see RELEASING.md). The two fields here are placeholders. deslopper has no runtime
# dependencies, so the formula needs no resource stanzas.
class Deslopper < Formula
  include Language::Python::Virtualenv

  desc "Deterministic prose linter for the mechanical tells of machine-generated writing"
  homepage "https://github.com/jv-k/deslopper"
  url "https://files.pythonhosted.org/packages/source/d/deslopper/deslopper-0.1.0.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "deslopper #{version}", shell_output("#{bin}/deslopper --version")
  end
end
