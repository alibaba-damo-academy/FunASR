# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pynini
from fun_text_processing.inverse_text_normalization.ko.utils import get_abs_path
from fun_text_processing.inverse_text_normalization.ko.graph_utils import (
    DAMO_ALPHA,
    DAMO_SIGMA,
    DAMO_DIGIT,
    DAMO_SPACE,
    DAMO_CHAR,
    GraphFst,
    delete_space,
    
)
from pynini.lib import pynutil

class CardinalFst(GraphFst):
    """
    Finite state transducer for classifying cardinals
        e.g. minus twenty three -> cardinal { integer: "23" negative: "-" } }
    Numbers below thirteen are not converted.
    """

    def __init__(self):
        super().__init__(name="cardinal", kind="classify")
        graph_zero = pynini.string_file(get_abs_path("data/numbers/zero.tsv"))

        graph_digit = pynini.string_file(get_abs_path("data/numbers/digit.tsv"))
        graph_teens_without_zero = pynini.string_file(get_abs_path("data/numbers/digit_teens_without_zero.tsv"))
        graph_teens = pynini.string_file(get_abs_path("data/numbers/digit_teens.tsv")) 

        graph_inh_digit = pynini.string_file(get_abs_path("data/numbers/digit_inherent_digit.tsv"))
        graph_inh_teen_without_zero = pynini.string_file(get_abs_path("data/numbers/digit_inherent_teens_without_zero.tsv"))
        graph_inh_teen = pynini.string_file(get_abs_path("data/numbers/digit_inherent_teens.tsv"))
        graph_inh_teen_others = pynini.string_file(get_abs_path("data/numbers/digit_inherent_others.tsv"))
        
        graph_less_hundred_num_inh_p1 = graph_inh_teen_without_zero + graph_inh_digit
        graph_less_hundred_num_inh = pynini.union(graph_inh_teen, graph_less_hundred_num_inh_p1, graph_inh_teen_others)

        graph_less_hundred_num_p1 = graph_teens_without_zero + graph_digit
        graph_less_hundred_num = pynini.union(graph_less_hundred_num_p1, graph_teens)

        #digits
        addzero = pynutil.insert("0")
        zero = graph_zero
        digits_combine = graph_digit | graph_inh_digit | zero
        digits = graph_digit | zero
        digit = graph_digit

        #teens
        teens_combine = graph_less_hundred_num | graph_less_hundred_num_inh
        #teens = graph_less_hundred_num 
        teens = teens_combine
        
        #hundred, #??? ?????? ???
        hundred = ( digit + pynutil.delete("???") + (teens
                                                    | pynutil.add_weight(zero + digit, 0.1)
                                                    | pynutil.add_weight(digit + addzero, 0.5)
                                                    | pynutil.add_weight(addzero**2, 1.0)))

        graph_hundred_component_at_least_one_none_zero_digit = hundred @ (
            pynini.closure(DAMO_DIGIT) + (DAMO_DIGIT - "0") + pynini.closure(DAMO_DIGIT)  
        )

        self.graph_hundred_component_at_least_one_none_zero_digit = (
            graph_hundred_component_at_least_one_none_zero_digit
        )

        ##thousand ??? ????????? 
        thousand = ((hundred | teens | digits) + pynutil.delete("???") + (
                     hundred
                     | pynutil.add_weight(zero + teens, 0.1)
                     | pynutil.add_weight(addzero + zero + digit, 0.5)
                     | pynutil.add_weight(digit + addzero**2, 0.8)
                     | pynutil.add_weight(addzero**3, 1.0))) 

        ##??? ?????????
        ten_thousand = ((thousand | hundred | teens | digits)
                        + pynutil.delete("???")
                        + pynini.cross(" ", "").ques
                        + (thousand
                           | pynutil.add_weight(zero + hundred, 0.1)
                           | pynutil.add_weight(addzero + zero + teens, 0.5)
                           | pynutil.add_weight(addzero + addzero + zero + digit, 0.5)
                           | pynutil.add_weight(digit + addzero**3, 0.8)
                           | pynutil.add_weight(addzero**4, 1.0)))

        ##???, ????????????  ???, ?????????
        number = digits | teens | hundred | thousand | ten_thousand
       
        ## ques is equal to pynini.closure(, 0, 1) 
        number = ((number + pynini.accep("???").ques + pynini.cross(" ", "").ques).ques + 
                  (number + pynini.accep("???").ques + pynini.cross(" ", "").ques).ques + number)        

        graph = number | graph_less_hundred_num_inh | graph_inh_digit | graph_inh_teen | graph_inh_teen_others
        #labels_exception = [num_to_word(x) for x in range(0, 13)]
        labels_exception = [ 'zzzzzzzzz' ]
        graph_exception = pynini.union(*labels_exception)
        
        self.graph_no_exception = graph

        self.graph = (pynini.project(graph, "input") - graph_exception.arcsort()) @ graph

        optional_minus_graph = pynini.closure(
            pynutil.insert("negative: ") + pynini.cross("????????????", "\"-\"") + DAMO_SPACE, 0, 1
        )

        final_graph = optional_minus_graph + pynutil.insert("integer: \"") + self.graph + pynutil.insert("\"")
        final_graph = self.add_tokens(final_graph)
        self.fst = final_graph.optimize()


