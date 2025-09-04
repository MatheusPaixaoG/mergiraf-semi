use diffy_imara as diffy;

///Textual merge result could be a conflict or not
#[derive(Debug, PartialEq, Eq)]
pub enum TextualMergeResult{
    Success(String),
    Conflict(String),
}

pub trait TextualMerger{
    fn merge(&self, base: &str, left: &str, right: &str) -> TextualMergeResult;
}

///diffy merge implementation
pub struct DiffyMerger;
impl TextualMerger for DiffyMerger {
    fn merge(&self, base: &str, left: &str, right: &str) -> TextualMergeResult {
        
        let result = diffy::merge(base, left, right);

        match result {
            Ok(merged_text) => TextualMergeResult::Success(merged_text),
            Err(conflict_text) => TextualMergeResult::Conflict(conflict_text),
        }
    }
}